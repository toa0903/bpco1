#!/usr/bin/env python3
"""Local PWA verification for BPCO OOH index.html (mobile 390x844 + desktop)."""
import asyncio
import json
import sys

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/bpco1/"
SHOT_DIR = sys.argv[2] if len(sys.argv) > 2 else "tools/shots"


async def run():
    logs, errors, requests_failed = [], [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page = await ctx.new_page()
        page.on("console", lambda m: logs.append((m.type, m.text)))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("requestfailed", lambda r: requests_failed.append((r.url, r.failure)))

        await page.goto(BASE, wait_until="networkidle")

        info = await page.evaluate(
            """() => ({
              w: window.innerWidth, h: window.innerHeight,
              manifest: document.querySelector('link[rel=manifest]')?.href,
              appleIcon: document.querySelector('link[rel="apple-touch-icon"]')?.href,
              title: document.querySelector('meta[name="apple-mobile-web-app-title"]')?.content,
              capable: document.querySelector('meta[name="apple-mobile-web-app-capable"]')?.content,
              barStyle: document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')?.content,
              themeColor: document.querySelector('meta[name="theme-color"]')?.content,
              viewport: document.querySelector('meta[name=viewport]')?.content,
              locked: document.body.classList.contains('auth-lock'),
            })"""
        )
        print("INFO", json.dumps(info, ensure_ascii=False))

        await page.screenshot(path=f"{SHOT_DIR}/m1-lock.png")

        # unlock with the team password
        await page.fill("#lockInput", "0815")
        await page.click("button[type=submit]")
        await page.wait_for_timeout(1500)
        unlocked = await page.evaluate(
            "() => ({locked: document.body.classList.contains('auth-lock'), "
            "lockHidden: document.getElementById('lockScreen').hidden, "
            "store: localStorage.getItem('bpco.ooh.team.access.v1')})"
        )
        print("UNLOCK", json.dumps(unlocked, ensure_ascii=False))
        await page.screenshot(path=f"{SHOT_DIR}/m2-list.png")

        # empty state / request count + sync note
        state = await page.evaluate(
            """() => {
              const cards = document.querySelectorAll('.req-card').length;
              const listTxt = document.querySelector('#viewList')?.innerText.trim().slice(0, 300);
              const sync = document.getElementById('syncNote')?.innerText.trim();
              const bodyPB = getComputedStyle(document.body).paddingBottom;
              const tabbar = document.querySelector('.tabbar');
              const tb = tabbar ? tabbar.getBoundingClientRect() : null;
              return {cards, sync, listTxt, bodyPB,
                      tabbarTop: tb && Math.round(tb.top), tabbarH: tb && Math.round(tb.height),
                      docH: document.documentElement.scrollHeight};
            }"""
        )
        print("STATE", json.dumps(state, ensure_ascii=False))

        # calendar tab (mobile bottom tab)
        try:
            await page.click('.tab[data-v="cal"]')
            await page.wait_for_timeout(600)
            await page.screenshot(path=f"{SHOT_DIR}/m3-cal.png")
        except Exception as e:
            print("TAB_CLICK_ERR", e)

        # service worker + manifest
        sw = await page.evaluate(
            """async () => {
              const regs = await navigator.serviceWorker.getRegistrations();
              const rs = await fetch('./manifest.webmanifest').then(r => ({s: r.status, t: r.headers.get('content-type')}));
              const icons = {};
              for (const f of ['apple-touch-icon.png','icon-192.png','icon-512.png','sw.js']) {
                const r = await fetch('./' + f, {method: 'HEAD'});
                icons[f] = r.status;
              }
              return {
                swCount: regs.length,
                swScopes: regs.map(r => r.scope),
                swActive: regs.map(r => !!r.active),
                controller: !!navigator.serviceWorker.controller,
                manifest: rs, icons
              };
            }"""
        )
        print("SW", json.dumps(sw, ensure_ascii=False))

        # wait for SW to take control then reload to confirm it is active
        await page.wait_for_timeout(1200)
        await page.reload(wait_until="networkidle")
        sw2 = await page.evaluate(
            """async () => {
              const regs = await navigator.serviceWorker.getRegistrations();
              return {controller: !!navigator.serviceWorker.controller,
                      active: regs.map(r => r.active && r.active.state)};
            }"""
        )
        print("SW_AFTER_RELOAD", json.dumps(sw2, ensure_ascii=False))

        # offline fallback: SW should serve the cached shell
        await ctx.set_offline(True)
        try:
            await page.reload(wait_until="domcontentloaded", timeout=15000)
            offline_ok = await page.evaluate(
                "() => ({title: document.title, lock: !!document.getElementById('lockScreen'), "
                "cards: document.querySelectorAll('.req-card').length})"
            )
        except Exception as e:
            offline_ok = {"error": str(e)}
        print("OFFLINE", json.dumps(offline_ok, ensure_ascii=False))
        await ctx.set_offline(False)

        # desktop view sanity
        page2 = await ctx.new_page()
        await page2.set_viewport_size({"width": 1440, "height": 900})
        await page2.goto(BASE, wait_until="networkidle")
        await page2.screenshot(path=f"{SHOT_DIR}/d1-desktop.png")

        print("CONSOLE", json.dumps(logs, ensure_ascii=False))
        print("PAGEERRORS", json.dumps(errors, ensure_ascii=False))
        print("REQFAILED", json.dumps(requests_failed[:10], ensure_ascii=False))
        await browser.close()


asyncio.run(run())
