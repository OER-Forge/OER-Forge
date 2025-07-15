document.addEventListener('DOMContentLoaded', function() {
  // --- Theme Toggle ---
  const themeBtn = document.getElementById('theme-toggle');
  const themeLink = document.getElementById('theme-css');

  function updateThemeButton() {
    if (!themeBtn || !themeLink) return;
    const href = themeLink.getAttribute('href');
    const isLight = href && href.includes('light');
    themeBtn.textContent = isLight ? '🌙' : '☀️';
    themeBtn.setAttribute('aria-label', isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode');
  }

  if (themeBtn && themeLink) {
    themeBtn.addEventListener('click', function() {
      const href = themeLink.getAttribute('href');
      const isLight = href && href.includes('light');
      // Compute correct relative path for theme CSS
      let basePath = href.replace(/theme-(light|dark)\.css$/, '');
      let newTheme = isLight ? 'theme-dark.css' : 'theme-light.css';
      themeLink.setAttribute('href', basePath + newTheme);
      updateThemeButton();
    });

    updateThemeButton();
  }

// Apply saved font settings on load
['font-family', 'font-size', 'letter-spacing', 'line-height'].forEach(function(setting) {
  const value = localStorage.getItem(setting);
  if (value) {
    if (setting === 'font-family') {
      document.body.style.fontFamily = value;
      const container = document.querySelector('.container');
      if (container) container.style.fontFamily = value;
      const markdownBody = document.querySelector('.markdown-body');
      if (markdownBody) markdownBody.style.fontFamily = value;
      // Set radio checked
      const radio = document.querySelector(`input[name="font-family"][value="${value}"]`);
      if (radio) radio.checked = true;
    } else {
      document.documentElement.style.setProperty('--' + setting, value);
      // Set radio checked
      const radio = document.querySelector(`input[name="${setting}"][value="${value}"]`);
      if (radio) radio.checked = true;
    }
  }
});

  // --- Font Appearance Controls ---
  document.querySelectorAll('.font-controls input[type=radio]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      localStorage.setItem(e.target.name, e.target.value);
      if (e.target.name === 'font-family') {
        document.body.style.fontFamily = e.target.value;
        const container = document.querySelector('.container');
        if (container) container.style.fontFamily = e.target.value;
        const markdownBody = document.querySelector('.markdown-body');
        if (markdownBody) markdownBody.style.fontFamily = e.target.value;
      } else {
        document.documentElement.style.setProperty('--' + e.target.name, e.target.value);
      }
    });
  });
});
// Font controls only on homepage
const fontControls = document.getElementById('font-controls');
if (fontControls) {
  document.querySelectorAll('input[name="font-family"]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      const value = e.target.value;
      document.body.style.fontFamily = value;
      const container = document.querySelector('.container');
      if (container) container.style.fontFamily = value;
      const markdownBody = document.querySelector('.markdown-body');
      if (markdownBody) markdownBody.style.fontFamily = value;
      localStorage.setItem('font-family', value);
    });
  });
  document.querySelectorAll('input[name="font-size"]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      const value = e.target.value;
      document.documentElement.style.setProperty('--font-size', value);
      localStorage.setItem('font-size', value);
    });
  });
  document.querySelectorAll('input[name="letter-spacing"]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      const value = e.target.value;
      document.documentElement.style.setProperty('--letter-spacing', value);
      localStorage.setItem('letter-spacing', value);
    });
  });
  document.querySelectorAll('input[name="line-height"]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      const value = e.target.value;
      document.documentElement.style.setProperty('--line-height', value);
      localStorage.setItem('line-height', value);
    });
  });
}