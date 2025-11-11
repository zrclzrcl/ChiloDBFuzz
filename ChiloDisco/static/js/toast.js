// ChiloDisco Toast 通知系统
(function() {
  // 创建 Toast 容器
  const container = document.createElement('div');
  container.id = 'cd-toast-container';
  container.className = 'cd-toast-container';
  
  // 等待 DOM 加载
  if (document.body) {
    document.body.appendChild(container);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      document.body.appendChild(container);
    });
  }

  // Toast 队列
  let toastId = 0;

  /**
   * 显示 Toast 通知
   * @param {string} message - 消息内容
   * @param {string} type - 类型：success, error, warning, info
   * @param {number} duration - 持续时间（毫秒），0 表示不自动关闭
   */
  function showToast(message, type = 'info', duration = 3000) {
    const id = ++toastId;
    const toast = document.createElement('div');
    toast.className = `cd-toast cd-toast-${type}`;
    toast.setAttribute('data-id', id);

    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };

    toast.innerHTML = `
      <div class="cd-toast-icon">${icons[type] || icons.info}</div>
      <div class="cd-toast-message">${message}</div>
      <button class="cd-toast-close" onclick="window.ChiloDisco.closeToast(${id})">✕</button>
    `;

    container.appendChild(toast);

    // 动画延迟
    requestAnimationFrame(() => {
      toast.classList.add('cd-toast-show');
    });

    // 自动关闭
    if (duration > 0) {
      setTimeout(() => {
        closeToast(id);
      }, duration);
    }

    return id;
  }

  /**
   * 关闭指定 Toast
   */
  function closeToast(id) {
    const toast = container.querySelector(`[data-id="${id}"]`);
    if (toast) {
      toast.classList.remove('cd-toast-show');
      toast.classList.add('cd-toast-hide');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }
  }

  /**
   * 关闭所有 Toast
   */
  function closeAllToasts() {
    const toasts = container.querySelectorAll('.cd-toast');
    toasts.forEach(toast => {
      const id = toast.getAttribute('data-id');
      closeToast(id);
    });
  }

  // 导出到全局
  window.ChiloDisco = window.ChiloDisco || {};
  window.ChiloDisco.showToast = showToast;
  window.ChiloDisco.closeToast = closeToast;
  window.ChiloDisco.closeAllToasts = closeAllToasts;

  // 便捷方法
  window.ChiloDisco.toast = {
    success: (msg, duration) => showToast(msg, 'success', duration),
    error: (msg, duration) => showToast(msg, 'error', duration),
    warning: (msg, duration) => showToast(msg, 'warning', duration),
    info: (msg, duration) => showToast(msg, 'info', duration),
  };
})();

// 全局加载指示器
(function() {
  const loader = document.createElement('div');
  loader.id = 'cd-global-loader';
  loader.className = 'cd-global-loader cd-loader-hidden';
  loader.innerHTML = `
    <div class="cd-loader-content">
      <div class="cd-loader-spinner"></div>
      <div class="cd-loader-text">加载中...</div>
    </div>
  `;

  if (document.body) {
    document.body.appendChild(loader);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      document.body.appendChild(loader);
    });
  }

  let loaderCount = 0;

  function showLoader(text = '加载中...') {
    loaderCount++;
    const textEl = loader.querySelector('.cd-loader-text');
    if (textEl) textEl.textContent = text;
    loader.classList.remove('cd-loader-hidden');
    loader.classList.add('cd-loader-show');
  }

  function hideLoader() {
    loaderCount = Math.max(0, loaderCount - 1);
    if (loaderCount === 0) {
      loader.classList.remove('cd-loader-show');
      loader.classList.add('cd-loader-hidden');
    }
  }

  window.ChiloDisco = window.ChiloDisco || {};
  window.ChiloDisco.showLoader = showLoader;
  window.ChiloDisco.hideLoader = hideLoader;
})();


