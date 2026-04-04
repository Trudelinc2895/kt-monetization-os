"""
stripe/setup_stripe.py
KT Monetization OS — Stripe bootstrap (run once)
Usage: python stripe/setup_stripe.py
"""
import os, json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    import stripe
except ImportError:
    raise SystemExit("pip install stripe python-dotenv")

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
assert stripe.api_key.startswith("sk_"), "Invalid STRIPE_SECRET_KEY"

MODE = "TEST" if stripe.api_key.startswith("sk_test_") else "LIVE"
DOMAIN = os.getenv("DOMAIN", "tkverse.ca")
print(f"[stripe-setup] mode={MODE}  domain={DOMAIN}")


PLANS = [
    {"key": "starter",  "name": "KT Starter",  "usd_monthly": 0,    "usd_yearly": 0,     "description": "Accès basique gratuit"},
    {"key": "pro",      "name": "KT Pro",       "usd_monthly": 2900, "usd_yearly": 29000, "description": "Modules 1-5 complets — 1,000 messages/mois"},
    {"key": "business", "name": "KT Business",  "usd_monthly": 9900, "usd_yearly": 99000, "description": "Tous les modules 1-10 — messages illimités"},
]

CREDIT_PACK = {
    "name": "KT Credits Pack (100 crédits)",
    "usd_cents": 999,  # $9.99 par pack de 100 crédits
    "credits": 100,
    "description": "Pack de 100 crédits IA — valable sans expiration",
}

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.created",
    "customer.deleted",
]


def upsert_product_and_price(plan: dict) -> dict:
    # Search existing product by metadata key
    existing = stripe.Product.search(query=f'metadata["plan_key"]:"{plan["key"]}"').data
    if existing:
        product = existing[0]
        print(f"  [exists] product {product.id} ({plan['name']})")
    else:
        product = stripe.Product.create(
            name=plan["name"],
            description=plan["description"],
            metadata={"plan_key": plan["key"]},
        )
        print(f"  [created] product {product.id} ({plan['name']})")

    if plan["usd_monthly"] == 0:
        return {"product_id": product.id, "price_monthly_id": "free", "price_yearly_id": "free"}

    existing_prices = stripe.Price.list(product=product.id, active=True).data

    # Monthly price
    monthly = [p for p in existing_prices if p.recurring and p.recurring.interval == "month"]
    if monthly:
        price_monthly = monthly[0]
        print(f"  [exists] monthly price {price_monthly.id} (${plan['usd_monthly']/100:.2f}/mo)")
    else:
        price_monthly = stripe.Price.create(
            product=product.id,
            unit_amount=plan["usd_monthly"],
            currency="usd",
            recurring={"interval": "month"},
            metadata={"plan_key": plan["key"], "interval": "monthly"},
        )
        print(f"  [created] monthly price {price_monthly.id} (${plan['usd_monthly']/100:.2f}/mo)")

    # Yearly price
    yearly = [p for p in existing_prices if p.recurring and p.recurring.interval == "year"]
    if yearly:
        price_yearly = yearly[0]
        print(f"  [exists] yearly price {price_yearly.id} (${plan['usd_yearly']/100:.2f}/yr)")
    else:
        price_yearly = stripe.Price.create(
            product=product.id,
            unit_amount=plan["usd_yearly"],
            currency="usd",
            recurring={"interval": "year"},
            metadata={"plan_key": plan["key"], "interval": "yearly"},
        )
        print(f"  [created] yearly price {price_yearly.id} (${plan['usd_yearly']/100:.2f}/yr)")

    return {
        "product_id": product.id,
        "price_monthly_id": price_monthly.id,
        "price_yearly_id": price_yearly.id,
    }


def upsert_credit_pack(pack: dict) -> str:
    """Create (or reuse) the one-time credit pack price."""
    existing = stripe.Product.search(query='metadata["product_key"]:"credit_pack"').data
    if existing:
        product = existing[0]
        print(f"  [exists] credit pack product {product.id}")
    else:
        product = stripe.Product.create(
            name=pack["name"],
            description=pack["description"],
            metadata={"product_key": "credit_pack", "credits": str(pack["credits"])},
        )
        print(f"  [created] credit pack product {product.id}")

    prices = stripe.Price.list(product=product.id, active=True).data
    one_time = [p for p in prices if not p.recurring]
    if one_time:
        price = one_time[0]
        print(f"  [exists] credit pack price {price.id} (${pack['usd_cents']/100:.2f})")
    else:
        price = stripe.Price.create(
            product=product.id,
            unit_amount=pack["usd_cents"],
            currency="usd",
            metadata={"product_key": "credit_pack", "credits": str(pack["credits"])},
        )
        print(f"  [created] credit pack price {price.id} (${pack['usd_cents']/100:.2f})")

    return price.id


def setup_webhook() -> stripe.WebhookEndpoint:
    url = f"https://{DOMAIN}/api/billing/webhook"
    existing = [w for w in stripe.WebhookEndpoint.list().data if w.url == url]
    if existing:
        wh = existing[0]
        print(f"  [exists] webhook {wh.id} -> {url}")
        return wh
    wh = stripe.WebhookEndpoint.create(
        url=url,
        enabled_events=WEBHOOK_EVENTS,
        description="KT Monetization OS webhook",
    )
    print(f"  [created] webhook {wh.id} -> {url}")
    print(f"  *** ADD TO .env: STRIPE_WEBHOOK_SECRET={wh.secret} ***")
    return wh


def setup_portal() -> stripe.billing_portal.Configuration:
    configs = stripe.billing_portal.Configuration.list(active=True).data
    if configs:
        print(f"  [exists] portal config {configs[0].id}")
        return configs[0]
    cfg = stripe.billing_portal.Configuration.create(
        business_profile={
            "headline": "Gérez votre abonnement KT Monetization OS",
            "privacy_policy_url": f"https://{DOMAIN}/privacy",
            "terms_of_service_url": f"https://{DOMAIN}/terms",
        },
        features={
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
            "payment_method_update": {"enabled": True},
            "invoice_history": {"enabled": True},
        },
    )
    print(f"  [created] portal config {cfg.id}")
    return cfg


def main():
    print("\n[1/4] Products & Prices")
    results = {}
    for plan in PLANS:
        results[plan["key"]] = upsert_product_and_price(plan)

    print("\n[2/4] Credit Pack")
    credit_price_id = upsert_credit_pack(CREDIT_PACK)

    print("\n[3/4] Webhook")
    wh = setup_webhook()

    print("\n[4/4] Customer Portal")
    setup_portal()

    # Save IDs
    os.makedirs("stripe", exist_ok=True)
    output = {
        "mode": MODE,
        "domain": DOMAIN,
        "generated_at": datetime.utcnow().isoformat(),
        "products": results,
        "credit_price_id": credit_price_id,
        "webhook_id": wh.id,
    }
    with open("stripe/stripe_ids.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n✅ stripe/stripe_ids.json saved")
    print("\n--- COPY TO .env ---")
    if results.get("pro", {}).get("price_monthly_id", "free") != "free":
        print(f"STRIPE_PRICE_PRO_MONTHLY_ID={results['pro']['price_monthly_id']}")
        print(f"STRIPE_PRICE_PRO_YEARLY_ID={results['pro']['price_yearly_id']}")
    if results.get("business", {}).get("price_monthly_id", "free") != "free":
        print(f"STRIPE_PRICE_BUSINESS_MONTHLY_ID={results['business']['price_monthly_id']}")
        print(f"STRIPE_PRICE_BUSINESS_YEARLY_ID={results['business']['price_yearly_id']}")
    print(f"STRIPE_CREDIT_PRICE_ID={credit_price_id}")
    print("--------------------")


if __name__ == "__main__":
    main()
