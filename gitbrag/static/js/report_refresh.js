/**
 * Auto-refresh functionality for report generation
 *
 * Automatically refreshes the page when a report is being generated or regenerated,
 * providing a seamless experience for users waiting for fresh data.
 */

;(function () {
  'use strict'

  // Configuration
  const CONFIG = {
    refreshIntervalMs: 10000, // Refresh every 10 seconds
    maxRefreshAttempts: 18, // Maximum 18 attempts (3 minutes total)
    countdownElementId: 'refresh-countdown'
  }

  // State
  let refreshCount = 0
  let countdownTimer = null
  let refreshTimer = null

  /**
   * Check if the page should auto-refresh based on presence of regeneration notices
   */
  function shouldAutoRefresh () {
    const generatingNotice = document.querySelector(
      '.alert.regenerating-notice'
    )
    return generatingNotice !== null
  }

  /**
   * Update the countdown timer display
   */
  function updateCountdown (secondsRemaining) {
    const countdownElement = document.getElementById(CONFIG.countdownElementId)
    if (countdownElement) {
      countdownElement.textContent = secondsRemaining
    }
  }

  /**
   * Start countdown timer
   */
  function startCountdown () {
    let secondsRemaining = CONFIG.refreshIntervalMs / 1000
    updateCountdown(secondsRemaining)

    countdownTimer = setInterval(function () {
      secondsRemaining--
      if (secondsRemaining <= 0) {
        clearInterval(countdownTimer)
        countdownTimer = null
      } else {
        updateCountdown(secondsRemaining)
      }
    }, 1000)
  }

  /**
   * Perform the page refresh
   */
  function refreshPage () {
    // Preserve query parameters and hash
    window.location.reload()
  }

  /**
   * Schedule the next refresh
   */
  function scheduleRefresh () {
    if (refreshCount >= CONFIG.maxRefreshAttempts) {
      console.log('Auto-refresh: Maximum refresh attempts reached')
      stopAutoRefresh()
      return
    }

    refreshCount++
    console.log(
      `Auto-refresh: Scheduling refresh ${refreshCount}/${CONFIG.maxRefreshAttempts}`
    )

    refreshTimer = setTimeout(function () {
      refreshPage()
    }, CONFIG.refreshIntervalMs)

    startCountdown()
  }

  /**
   * Stop auto-refresh
   */
  function stopAutoRefresh () {
    if (countdownTimer) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
    console.log('Auto-refresh: Stopped')
  }

  /**
   * Initialize auto-refresh if conditions are met
   */
  function initialize () {
    if (shouldAutoRefresh()) {
      console.log('Auto-refresh: Enabled')
      scheduleRefresh()
    } else {
      console.log('Auto-refresh: Not needed')
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize)
  } else {
    // DOM is already ready
    initialize()
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', stopAutoRefresh)
})()
