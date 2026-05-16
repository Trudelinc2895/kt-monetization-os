"""backend/api/scraping/stealth/fingerprint.py — Playwright stealth patches."""
from __future__ import annotations

import json

from api.scraping.stealth.headers import get_stealth_profile

_STEALTH_SCRIPT_TEMPLATE = """
(function() {
    if (window.__nanovia_stealth_applied) return;
    window.__nanovia_stealth_applied = true;

    const languages = {languages};
    const platform = {platform};
    const webglVendor = {webgl_vendor};
    const webglRenderer = {webgl_renderer};
    const canvasShift = {canvas_shift};

    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
    } catch(e) {}

    try {
        Object.defineProperty(navigator, 'platform', {
            get: () => platform,
            configurable: true,
        });
    } catch(e) {}

    try {
        const fakePlugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const arr = fakePlugins.map(p => Object.assign(Object.create(Plugin.prototype || {}), p));
                Object.defineProperty(arr, 'length', { value: fakePlugins.length });
                return arr;
            },
            configurable: true,
        });
    } catch(e) {}

    try {
        Object.defineProperty(navigator, 'languages', {
            get: () => languages,
            configurable: true,
        });
    } catch(e) {}

    try {
        if (!window.chrome) {
            Object.defineProperty(window, 'chrome', {
                value: { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} },
                writable: false,
                configurable: true,
            });
        }
    } catch(e) {}

    try {
        const origQuery = window.navigator.permissions && window.navigator.permissions.query.bind(window.navigator.permissions);
        if (origQuery) {
            window.navigator.permissions.query = (params) => {
                if (params.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission });
                }
                return origQuery(params);
            };
        }
    } catch(e) {}

    try {
        const getParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return webglVendor;
            if (parameter === 37446) return webglRenderer;
            return getParam.apply(this, arguments);
        };
    } catch(e) {}

    try {
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' && canvasShift !== 0) {
                const ctx = this.getContext('2d');
                if (ctx && this.width > 0 && this.height > 0) {
                    try {
                        const img = ctx.getImageData(0, 0, 1, 1);
                        img.data[0] = Math.max(0, Math.min(255, img.data[0] + canvasShift));
                        ctx.putImageData(img, 0, 0);
                    } catch(e) {}
                }
            }
            return origToDataURL.apply(this, arguments);
        };
    } catch(e) {}
})();
"""


def render_stealth_script(profile: dict[str, object] | None = None) -> str:
    p = profile or get_stealth_profile()
    return _STEALTH_SCRIPT_TEMPLATE.format(
        languages=json.dumps(p.get("languages", ["en-US", "en"])),
        platform=json.dumps(str(p.get("platform", "Win32"))),
        webgl_vendor=json.dumps(str(p.get("webgl_vendor", "Intel Inc."))),
        webgl_renderer=json.dumps(str(p.get("webgl_renderer", "Intel Iris OpenGL Engine"))),
        canvas_shift=json.dumps(int(p.get("canvas_shift", 1))),
    )


async def apply_stealth_patches(page, profile: dict[str, object] | None = None) -> None:
    await page.add_init_script(render_stealth_script(profile))
