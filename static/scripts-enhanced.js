/**
 * Enhanced Portfolio JavaScript
 * Version: 2.0.0
 * Provides interactive features, form validation, and user experience improvements
 */

/* ===== INITIALIZATION ===== */
document.addEventListener("DOMContentLoaded", function () {
  initializeMobileMenu();
  initializeFormValidation();
  initializeSmoothScroll();
  initializeScrollAnimations();
  initializeTooltips();
  setupEventTracking();
});

/* ===== MOBILE MENU TOGGLE ===== */
function initializeMobileMenu() {
  const mobileToggle = document.querySelector(".mobile-nav-toggle");
  const navbar = document.querySelector(".navbar ul");

  if (!mobileToggle || !navbar) return;

  mobileToggle.addEventListener("click", function () {
    navbar.classList.toggle("show");
    mobileToggle.setAttribute(
      "aria-expanded",
      mobileToggle.getAttribute("aria-expanded") === "false" ? "true" : "false"
    );
  });

  // Close menu when link is clicked
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", function () {
      navbar.classList.remove("show");
      mobileToggle.setAttribute("aria-expanded", "false");
    });
  });
}

/* ===== FORM VALIDATION ===== */
function initializeFormValidation() {
  const forms = document.querySelectorAll("form");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      if (!validateForm(this)) {
        e.preventDefault();
      }
    });

    // Real-time validation
    const inputs = form.querySelectorAll("input, textarea");
    inputs.forEach((input) => {
      input.addEventListener("blur", function () {
        validateField(this);
      });

      input.addEventListener("input", function () {
        if (this.classList.contains("is-invalid")) {
          validateField(this);
        }
      });
    });
  });
}

function validateForm(form) {
  let isValid = true;
  const fields = form.querySelectorAll("[required]");

  fields.forEach((field) => {
    if (!validateField(field)) {
      isValid = false;
    }
  });

  return isValid;
}

function validateField(field) {
  const errorContainer = field.parentElement.querySelector(".form-error");
  const value = field.value.trim();
  let error = "";

  // Check if field is empty
  if (field.hasAttribute("required") && !value) {
    error = field.dataset.errorRequired || "This field is required";
  }

  // Email validation
  if (field.type === "email" && value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      error = field.dataset.errorEmail || "Please enter a valid email address";
    }
  }

  // Length validation
  if (field.minLength && value.length > 0 && value.length < field.minLength) {
    error = `Must be at least ${field.minLength} characters`;
  }

  if (field.maxLength && value.length > field.maxLength) {
    error = `Must be no more than ${field.maxLength} characters`;
  }

  // Pattern validation
  if (field.pattern && value && !new RegExp(field.pattern).test(value)) {
    error = field.dataset.errorPattern || "Invalid format";
  }

  // Display or clear error
  if (error) {
    field.classList.add("is-invalid");
    if (errorContainer) {
      errorContainer.textContent = error;
      errorContainer.style.display = "block";
    }
    return false;
  } else {
    field.classList.remove("is-invalid");
    if (errorContainer) {
      errorContainer.style.display = "none";
    }
    return true;
  }
}

/* ===== SMOOTH SCROLLING ===== */
function initializeSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");
      if (href === "#") return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });
}

/* ===== SCROLL ANIMATIONS ===== */
function initializeScrollAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animate-in");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    }
  );

  document.querySelectorAll(".card, .info-box, section").forEach((el) => {
    observer.observe(el);
  });
}

/* ===== TOOLTIPS ===== */
function initializeTooltips() {
  const tooltipElements = document.querySelectorAll("[data-tooltip]");

  tooltipElements.forEach((element) => {
    element.addEventListener("mouseenter", function () {
      const tooltip = document.createElement("div");
      tooltip.className = "tooltip";
      tooltip.textContent = this.dataset.tooltip;
      document.body.appendChild(tooltip);

      const rect = this.getBoundingClientRect();
      tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + "px";
      tooltip.style.left =
        rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + "px";

      this.dataset.tooltipId = tooltip;
    });

    element.addEventListener("mouseleave", function () {
      if (this.dataset.tooltipId) {
        this.dataset.tooltipId.remove();
        delete this.dataset.tooltipId;
      }
    });
  });
}

/* ===== FORM SUBMISSION FEEDBACK ===== */
function setupFormSubmissionFeedback() {
  const forms = document.querySelectorAll("form");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn) {
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending...";

        // Re-enable after submission
        setTimeout(() => {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }, 3000);
      }
    });
  });
}

/* ===== DYNAMIC CHARACTER COUNTER ===== */
function initializeCharacterCounter() {
  const textareas = document.querySelectorAll("textarea[maxlength]");

  textareas.forEach((textarea) => {
    const maxLength = textarea.maxLength;
    const counter = document.createElement("small");
    counter.className = "char-counter";
    counter.style.display = "block";
    counter.style.marginTop = "0.5rem";
    counter.style.color = "var(--text-muted)";

    textarea.parentElement.appendChild(counter);

    function updateCounter() {
      const remaining = maxLength - textarea.value.length;
      counter.textContent = `${textarea.value.length}/${maxLength} characters`;

      if (remaining < 100) {
        counter.style.color =
          remaining < 50 ? "var(--error-color)" : "var(--warning-color)";
      } else {
        counter.style.color = "var(--text-muted)";
      }
    }

    textarea.addEventListener("input", updateCounter);
    updateCounter();
  });
}

/* ===== ANALYTICS & EVENT TRACKING ===== */
function setupEventTracking() {
  // Track button clicks
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      trackEvent("button_click", {
        button_text: this.textContent,
        button_class: this.className,
      });
    });
  });

  // Track form submissions
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", function () {
      trackEvent("form_submit", {
        form_name: this.name || "unknown",
      });
    });
  });

  // Track link clicks
  document.querySelectorAll('a[href^="http"]').forEach((link) => {
    link.addEventListener("click", function () {
      trackEvent("external_link_click", {
        url: this.href,
      });
    });
  });
}

function trackEvent(eventName, properties = {}) {
  // Log to console in development
  if (typeof console !== "undefined") {
    console.log(`Event: ${eventName}`, properties);
  }

  // Send to analytics service if available
  if (typeof gtag !== "undefined") {
    gtag("event", eventName, properties);
  }
}

/* ===== UTILITIES ===== */

/**
 * Debounce function for performance optimization
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function for performance optimization
 */
function throttle(func, limit) {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Show/hide loading spinner
 */
function showLoadingSpinner(show = true) {
  let spinner = document.getElementById("loading-spinner");

  if (show && !spinner) {
    spinner = document.createElement("div");
    spinner.id = "loading-spinner";
    spinner.className = "spinner";
    spinner.innerHTML = '<div class="spinner-border"></div>';
    document.body.appendChild(spinner);
  } else if (!show && spinner) {
    spinner.remove();
  }
}

/**
 * Display toast notification
 */
function showToast(message, type = "info", duration = 3000) {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("show");
  }, 100);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Clone form to reset after submission
 */
function resetForm(formId) {
  const form = document.getElementById(formId);
  if (form) {
    form.reset();
    form.querySelectorAll(".form-error").forEach((error) => {
      error.style.display = "none";
    });
    form.querySelectorAll(".is-invalid").forEach((field) => {
      field.classList.remove("is-invalid");
    });
  }
}

/**
 * Keyboard navigation support
 */
function setupKeyboardNavigation() {
  document.addEventListener("keydown", function (e) {
    // ESC to close mobile menu
    if (e.key === "Escape") {
      const navbar = document.querySelector(".navbar ul");
      if (navbar) {
        navbar.classList.remove("show");
      }
    }
  });
}

/* ===== INITIALIZE ALL FEATURES ===== */
document.addEventListener("DOMContentLoaded", function () {
  setupFormSubmissionFeedback();
  initializeCharacterCounter();
  setupKeyboardNavigation();
});

/**
 * Export functions for external use
 */
window.PortfolioApp = {
  validateForm,
  validateField,
  showToast,
  showLoadingSpinner,
  resetForm,
  trackEvent,
  debounce,
  throttle,
};
