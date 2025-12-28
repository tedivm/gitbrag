// Theme toggle functionality
;(function () {
  // Get theme from localStorage or default to system preference
  function getTheme () {
    const stored = localStorage.getItem('theme')
    if (stored) {
      return stored
    }
    // Check system preference
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    ) {
      return 'dark'
    }
    return 'light'
  }

  // Set theme on document root
  function setTheme (theme) {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
    updateToggleButton(theme)
  }

  // Update toggle button icon
  function updateToggleButton (theme) {
    const button = document.getElementById('theme-toggle')
    if (button) {
      button.textContent = theme === 'dark' ? '☀️' : '🌙'
      button.setAttribute(
        'aria-label',
        theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
      )
    }
  }

  // Toggle between light and dark
  function toggleTheme () {
    const currentTheme =
      document.documentElement.getAttribute('data-theme') || getTheme()
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
  }

  // Initialize theme on page load
  function initTheme () {
    const theme = getTheme()
    setTheme(theme)
  }

  // Listen for system theme changes
  if (window.matchMedia) {
    window
      .matchMedia('(prefers-color-scheme: dark)')
      .addEventListener('change', e => {
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
          setTheme(e.matches ? 'dark' : 'light')
        }
      })
  }

  // Initialize immediately
  initTheme()

  // Attach toggle function to window for button onclick
  window.toggleTheme = toggleTheme

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme)
  }
})()
