// ==UserScript==
// @name         GLaDOS 自动签到（MutationObserver 版）
// @namespace    http://tampermonkey.net/
// @version      0.6
// @description  等待签到按钮出现后自动点击（排除已签到状态，兼容 Turnstile）
// @match        https://glados.cloud/console/checkin*
// @match        https://glados.network/console/checkin*
// @grant        none
// @license MIT
// ==/UserScript==

(function () {
    'use strict';

    const CLICKED_FLAG = '__glados_checkin_clicked__';

    // 找签到按钮：文本含 签到/checkin/sign in，排除「已签到」和 is-done/disabled 状态
    function findCheckinButton() {
        return [...document.querySelectorAll('button')].find(btn => {
            const text = (btn.innerText || '').toLowerCase();
            const isDone = btn.classList.contains('is-done') ||
                           (btn.innerText || '').includes('已签到') ||
                           text.includes('already') ||
                           btn.disabled;
            return (
                (text.includes('签到') || text.includes('checkin') || text.includes('sign in')) &&
                !isDone &&
                btn.offsetParent !== null
            );
        });
    }

    function doCheckin(button) {
        // 同一会话只点一次，防止 MutationObserver 多次触发
        if (window[CLICKED_FLAG]) return;
        window[CLICKED_FLAG] = true;
        console.log('✅ 找到可用签到按钮，执行点击');
        button.click();
    }

    // MutationObserver：按钮渲染出来就点
    const observer = new MutationObserver(() => {
        const button = findCheckinButton();
        if (button) {
            observer.disconnect();
            doCheckin(button);
        }
    });

    function start() {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true
        });
        // 初始检查（按钮可能已在 DOM 里，等不到 Mutation）
        setTimeout(() => {
            const button = findCheckinButton();
            if (button) {
                observer.disconnect();
                doCheckin(button);
            }
        }, 2000);
    }

    if (document.body) {
        start();
    } else {
        document.addEventListener('DOMContentLoaded', start);
    }

    console.log('🔍 GLaDOS 自动签到已启动，等待签到按钮...');
})();
