document.addEventListener('DOMContentLoaded', function() {
  // --- Theme Toggle ---
  const themeBtn = document.getElementById('theme-toggle');
  const themeLink = document.getElementById('theme-css');

  // --- Accessibility Report: Default to dark mode, persist with localStorage ---
  if (themeLink) {
    let savedTheme = localStorage.getItem('theme') || 'dark';
    localStorage.setItem('theme', savedTheme);
    const basePath = themeLink.getAttribute('href').replace(/theme-(light|dark)\.css$/, '');
    const newTheme = (savedTheme === 'dark') ? 'theme-dark.css' : 'theme-light.css';
    themeLink.setAttribute('href', basePath + newTheme);
  }

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
      const basePath = href.replace(/theme-(light|dark)\.css$/, '');
      const newTheme = isLight ? 'theme-dark.css' : 'theme-light.css';
      themeLink.setAttribute('href', basePath + newTheme);
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
      updateThemeButton();
    });
    updateThemeButton();
  }

  // --- Font Appearance Controls ---
  function applyFontSetting(setting, value) {
    if (setting === 'font-family') {
      document.body.style.fontFamily = value;
      document.querySelectorAll('.container, .markdown-body').forEach(el => el.style.fontFamily = value);
    } else {
      document.documentElement.style.setProperty('--' + setting, value);
    }
    // Set radio checked
    const radio = document.querySelector(`input[name="${setting}"][value="${value}"]`);
    if (radio) radio.checked = true;
  }

  ['font-family', 'font-size', 'letter-spacing', 'line-height'].forEach(function(setting) {
    const value = localStorage.getItem(setting);
    if (value) applyFontSetting(setting, value);
  });

  document.querySelectorAll('.font-controls input[type=radio]').forEach(function(radio) {
    radio.addEventListener('change', function(e) {
      localStorage.setItem(e.target.name, e.target.value);
      applyFontSetting(e.target.name, e.target.value);
    });
  });

  // --- Font controls only on homepage ---
  const fontControls = document.getElementById('font-controls');
  if (fontControls) {
    ['font-family', 'font-size', 'letter-spacing', 'line-height'].forEach(function(setting) {
      document.querySelectorAll(`input[name="${setting}"]`).forEach(function(radio) {
        radio.addEventListener('change', function(e) {
          applyFontSetting(setting, e.target.value);
          localStorage.setItem(setting, e.target.value);
        });
      });
    });
  }
});