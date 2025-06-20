// ==UserScript==
// @name         GLaDOS 自动签到（MutationObserver 版）
// @namespace    http://tampermonkey.net/
// @version      0.5
// @description  使用 MutationObserver 等待遮罩消失后自动点击签到
// @match        https://glados.network/console/checkin*
// @grant        none
// @license MIT
// ==/UserScript==
 
(function () {
    'use strict';
   
    function simulateClick(element) {
      const evt = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });
      element.dispatchEvent(evt);
    }
   
    function isHUDVisible() {
      const hud = document.querySelector('.ant-spin-spinning');
      return hud && window.getComputedStyle(hud).display !== 'none';
    }
   
    function tryCheckin() {
      const button = [...document.querySelectorAll('button')]
        .find(btn => btn.innerText.includes("签到") || btn.innerText.toLowerCase().includes("checkin"));
   
      if (button) {
        console.log("✅ 找到签到按钮，触发点击");
        simulateClick(button);
      } else {
        console.log("❌ 没找到签到按钮");
      }
    }
   
    function waitForHUDToDisappear() {
      const observer = new MutationObserver(() => {
        if (!isHUDVisible()) {
          console.log("✅ HUD 已消失，执行签到");
          observer.disconnect(); // 停止监听
          tryCheckin();
        }
      });
   
      // 监听整个页面 DOM 变化（subtree 表示递归所有子节点）
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true
      });
   
      console.log("📡 MutationObserver 启动，等待 HUD 消失...");
    }
   
    window.addEventListener('load', () => {
      waitForHUDToDisappear();
    });
  })();