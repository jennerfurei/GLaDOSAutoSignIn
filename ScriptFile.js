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
   
    function forceCheckIn() {
  // 强制停止页面加载
  window.stop();
  console.log("🛑 已强制停止页面加载");

  // 打印所有按钮的文本和类名（调试用）
  const buttons = [...document.querySelectorAll('button')];
  console.log("📋 当前页面按钮列表：", buttons.map(btn => ({
    text: btn.innerText,
    class: btn.className,
    disabled: btn.disabled,
    visible: btn.offsetParent !== null
  })));

  // 查找签到按钮（放宽匹配条件）
  const button = buttons.find(btn => {
    const text = btn.innerText.toLowerCase();
    return (
      (text.includes('签到') || text.includes('checkin') || text.includes('sign in')) &&
      !btn.disabled &&
      btn.offsetParent !== null
    );
  });

  if (button) {
    console.log("✅ 找到可用签到按钮，执行点击");
    button.click();
  } else {
    console.log("❌ 未找到可用签到按钮");
  }
}

// 使用 MutationObserver 监听 DOM 变化
const observer = new MutationObserver((mutations) => {
  console.log("🔍 检测到 DOM 变化，尝试查找按钮");
  const buttons = [...document.querySelectorAll('button')];
  const button = buttons.find(btn => {
    const text = btn.innerText.toLowerCase();
    return (
      (text.includes('签到') || text.includes('checkin') || text.includes('sign in')) &&
      !btn.disabled &&
      btn.offsetParent !== null
    );
  });

  if (button) {
    console.log("🎯 按钮已出现，准备执行签到");
    observer.disconnect();
    forceCheckIn();
  }
});

// 监听整个文档的 DOM 变化
observer.observe(document.body, {
  childList: true,
  subtree: true,
  attributes: true,
  characterData: true
});

console.log("🔍 启动 DOM 监听，等待签到按钮出现...");

// 初始检查（避免按钮已存在但未被监听捕获）
setTimeout(() => {
  const buttons = [...document.querySelectorAll('button')];
  const button = buttons.find(btn => {
    const text = btn.innerText.toLowerCase();
    return (
      (text.includes('签到') || text.includes('checkin') || text.includes('sign in')) &&
      !btn.disabled &&
      btn.offsetParent !== null
    );
  });

  if (button) {
    console.log("⚡ 按钮已存在，直接执行签到");
    forceCheckIn();
  }
}, 1000);
   
    // 同时监听 DOMContentLoaded 和 load 事件
window.addEventListener('DOMContentLoaded', () => {
  waitForButtonToAppear();
});

window.addEventListener('load', () => {
  waitForButtonToAppear();
});
  })();