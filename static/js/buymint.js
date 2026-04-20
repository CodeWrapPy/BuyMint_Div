/**
 * buymint.js — Shared client-side logic for BuyMint
 * Handles: Auth, Cart, Favorites, Toast notifications, UI helpers
 */

// ─── API Helper ──────────────────────────────────────────────
const API = {
  async _fetch(url, options = {}) {
    // BUG FIX #21: No try/catch around fetch() — any network error (offline,
    // timeout, CORS rejection) threw an unhandled Promise rejection and left
    // every button that called Cart/Auth/Favorites silently broken with no
    // user-visible feedback.  Now we catch and surface a friendly error.
    try {
      const res  = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options,
      });
      const data = await res.json();
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      console.error("Network error:", err);
      return {
        ok: false,
        status: 0,
        data: { error: "Network error. Please check your connection and try again." },
      };
    }
  },
  get:    (url)        => API._fetch(url, { method: "GET" }),
  post:   (url, body)  => API._fetch(url, { method: "POST",   body: JSON.stringify(body) }),
  put:    (url, body)  => API._fetch(url, { method: "PUT",    body: JSON.stringify(body) }),
  delete: (url, body)  => API._fetch(url, { method: "DELETE", body: body ? JSON.stringify(body) : undefined }),
};

// ─── Toast Notifications ────────────────────────────────────
const Toast = {
  _container: null,

  _getContainer() {
    if (!this._container) {
      this._container = document.createElement("div");
      this._container.id = "toast-container";
      this._container.style.cssText =
        "position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;";
      document.body.appendChild(this._container);
    }
    return this._container;
  },

  show(message, type = "success", duration = 3500) {
    const container = this._getContainer();
    const colors = {
      success: "#384e2d",
      error:   "#ba1a1a",
      info:    "#715a3e",
      warning: "#b4630a",
    };
    const icons = { success: "check_circle", error: "error", info: "info", warning: "warning" };

    const toast = document.createElement("div");
    toast.style.cssText = `
      background:${colors[type] || colors.success};color:#fff;
      padding:14px 20px;border-radius:1rem;font-size:14px;font-weight:600;
      display:flex;align-items:center;gap:10px;box-shadow:0 8px 24px rgba(0,0,0,.15);
      transform:translateX(120%);transition:transform .3s ease;max-width:360px;
      font-family:'Inter',sans-serif;
    `;

    // BUG FIX #22: Toast.show() was building its message via innerHTML with
    // the raw message string, which was also used to display API error text.
    // A malicious server response (or a compromised API call) could inject
    // arbitrary HTML/JS via that error string → XSS.
    // Fix: create the icon element normally, then set the text via a text node
    // so no HTML interpretation happens on the message content.
    const icon = document.createElement("span");
    icon.className = "material-symbols-outlined";
    icon.style.fontSize = "20px";
    icon.textContent = icons[type] || "info";

    const text = document.createTextNode(message);
    toast.appendChild(icon);
    toast.appendChild(text);

    container.appendChild(toast);

    requestAnimationFrame(() => { toast.style.transform = "translateX(0)"; });

    setTimeout(() => {
      toast.style.transform = "translateX(120%)";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success: (msg) => Toast.show(msg, "success"),
  error:   (msg) => Toast.show(msg, "error"),
  info:    (msg) => Toast.show(msg, "info"),
};

// ─── Cart ────────────────────────────────────────────────────
const Cart = {
  async add(productId, quantity = 1, btn = null) {
    if (btn) { btn.disabled = true; btn.style.opacity = "0.7"; }
    const { ok, data } = await API.post("/api/cart/", { product_id: productId, quantity });
    if (btn) { btn.disabled = false; btn.style.opacity = "1"; }

    if (ok) {
      Toast.success("Added to cart!");
      Cart._updateBadges(data.cart?.item_count ?? 0);
    } else {
      if (data.error && data.error.toLowerCase().includes("log in")) {
        Toast.info("Please log in to add items to your cart.");
        setTimeout(() => { window.location.href = "/login"; }, 1500);
      } else {
        Toast.error(data.error || "Could not add to cart.");
      }
    }
    return { ok, data };
  },

  async remove(itemId) {
    const { ok, data } = await API.delete(`/api/cart/${itemId}`);
    if (ok) {
      Toast.success("Item removed.");
      Cart._updateBadges(data.cart?.item_count ?? 0);
    } else {
      Toast.error(data.error || "Could not remove item.");
    }
    return { ok, data };
  },

  async update(itemId, quantity) {
    const { ok, data } = await API.put(`/api/cart/${itemId}`, { quantity });
    if (!ok) Toast.error(data.error || "Could not update cart.");
    return { ok, data };
  },

  async load() {
    const { ok, data } = await API.get("/api/cart/");
    return ok ? data : null;
  },

  _updateBadges(count) {
    document.querySelectorAll(".cart-badge, [data-cart-count]").forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? "flex" : "none";
    });
  },
};

// ─── Favorites ───────────────────────────────────────────────
const Favorites = {
  async toggle(productId, btn = null) {
    const { ok, data } = await API.post(`/api/favorites/${productId}/toggle`);
    if (ok) {
      const isFav = data.is_favorite;
      Toast.success(isFav ? "Added to favorites!" : "Removed from favorites.");
      if (btn) {
        btn.querySelector(".material-symbols-outlined").style.fontVariationSettings =
          isFav
            ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24"
            : "'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24";
      }
    } else {
      if (data.error && data.error.toLowerCase().includes("log in")) {
        Toast.info("Please log in to save favorites.");
        setTimeout(() => { window.location.href = "/login"; }, 1500);
      } else {
        Toast.error(data.error || "Could not update favorites.");
      }
    }
    return { ok, data };
  },
};

// ─── Auth ────────────────────────────────────────────────────
const Auth = {
  async login(email, password, remember = false) {
    return API.post("/api/auth/login", { email, password, remember });
  },

  async register(full_name, email, password) {
    return API.post("/api/auth/register", { full_name, email, password });
  },

  async logout() {
    const { ok } = await API.post("/api/auth/logout");
    if (ok) window.location.href = "/";
  },
};

// ─── Contact ─────────────────────────────────────────────────
const Contact = {
  async send(name, email, subject, message) {
    return API.post("/api/contact/", { name, email, subject, message });
  },
};

// ─── Safe HTML helpers ───────────────────────────────────────
/**
 * Escape a string so it is safe to inject into innerHTML contexts.
 * Used anywhere we build an HTML string that must include user/API-sourced text.
 */
function _escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * BUG FIX #23: Both the login and signup error message boxes were built with:
 *   msgBox.innerHTML = `...<span>...</span> ${data.error}`
 * If data.error contained any HTML characters, the browser would parse them,
 * giving a malicious server response (or network MITM) a foothold for XSS.
 * _setAuthError() now escapes the error string before inserting it.
 */
function _setAuthError(msgBox, message) {
  msgBox.className =
    "mb-4 p-4 rounded-xl text-sm font-medium flex items-center gap-2 " +
    "bg-red-50 text-red-700 border border-red-100";
  msgBox.innerHTML =
    `<span class="material-symbols-outlined">error</span> ${_escHtml(message)}`;
  msgBox.classList.remove("hidden");
}

function _setAuthSuccess(msgBox, message) {
  msgBox.className =
    "mb-4 p-4 rounded-xl text-sm font-medium flex items-center gap-2 " +
    "bg-emerald-50 text-emerald-700";
  msgBox.innerHTML =
    `<span class="material-symbols-outlined">check_circle</span> ${_escHtml(message)}`;
  msgBox.classList.remove("hidden");
}

// ─── Login Form Handler ──────────────────────────────────────
function initLoginForm() {
  const form = document.getElementById("login-form");
  if (!form) return;

  // Toggle password visibility
  document.querySelectorAll("[data-toggle-password]").forEach(btn => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.togglePassword);
      const icon  = btn.querySelector(".material-symbols-outlined");
      if (input.type === "password") {
        input.type = "text";
        if (icon) icon.textContent = "visibility_off";
      } else {
        input.type = "password";
        if (icon) icon.textContent = "visibility";
      }
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email    = form.querySelector('[name="email"]').value.trim();
    const password = form.querySelector('[name="password"]').value;
    const remember = form.querySelector('[name="remember"]')?.checked ?? false;
    const btn      = form.querySelector('[type="submit"]');
    const msgBox   = document.getElementById("auth-message");

    if (msgBox) msgBox.classList.add("hidden");
    btn.disabled    = true;
    btn.textContent = "Verifying…";

    const { ok, data } = await Auth.login(email, password, remember);

    if (ok) {
      if (msgBox) _setAuthSuccess(msgBox, "Login successful! Redirecting…");
      setTimeout(() => { window.location.href = "/home"; }, 900);
    } else {
      btn.disabled = false;
      btn.innerHTML = `Login <span class="material-symbols-outlined text-[20px]">arrow_forward</span>`;
      const errMsg = data.error || "Login failed.";
      if (msgBox) {
        _setAuthError(msgBox, errMsg);
      } else {
        Toast.error(errMsg);
      }
    }
  });
}

// ─── Signup Form Handler ─────────────────────────────────────
function initSignupForm() {
  const form = document.getElementById("signup-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const full_name = form.querySelector('[name="full_name"]').value.trim();
    const email     = form.querySelector('[name="email"]').value.trim();
    const password  = form.querySelector('[name="password"]').value;
    const btn       = form.querySelector('[type="submit"]');
    const msgBox    = document.getElementById("auth-message");

    if (password.length < 6) {
      Toast.error("Password must be at least 6 characters.");
      return;
    }

    if (msgBox) msgBox.classList.add("hidden");
    btn.disabled    = true;
    btn.textContent = "Creating account…";

    const { ok, data } = await Auth.register(full_name, email, password);

    if (ok) {
      Toast.success("Account created! Welcome to BuyMint 🌱");
      setTimeout(() => { window.location.href = "/home"; }, 1000);
    } else {
      btn.disabled    = false;
      btn.textContent = "Sign Up";
      const errMsg = data.error || "Sign up failed.";
      if (msgBox) {
        _setAuthError(msgBox, errMsg);
      } else {
        Toast.error(errMsg);
      }
    }
  });
}

// ─── Contact Form Handler ────────────────────────────────────
function initContactForm() {
  const form = document.getElementById("contact-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name    = form.querySelector('[name="name"]').value.trim();
    const email   = form.querySelector('[name="email"]').value.trim();
    const subject = form.querySelector('[name="subject"]')?.value.trim() || "";
    const message = form.querySelector('[name="message"]').value.trim();
    const btn     = form.querySelector('[type="submit"]');

    btn.disabled    = true;
    btn.textContent = "Sending…";

    const { ok, data } = await Contact.send(name, email, subject, message);

    btn.disabled    = false;
    btn.textContent = "Send Message";

    if (ok) {
      Toast.success(data.message || "Message sent!");
      form.reset();
    } else {
      Toast.error(data.error || "Could not send message.");
    }
  });
}

// ─── Logout buttons ──────────────────────────────────────────
function initLogoutButtons() {
  document.querySelectorAll("[data-action='logout']").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      Auth.logout();
    });
  });
}

// ─── Profile Form ────────────────────────────────────────────
function initProfileForm() {
  const form = document.getElementById("profile-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const full_name = form.querySelector('[name="full_name"]')?.value.trim();
    const phone     = form.querySelector('[name="phone"]')?.value.trim();
    const address   = form.querySelector('[name="address"]')?.value.trim();
    const btn       = form.querySelector('[type="submit"]');

    btn.disabled    = true;
    btn.textContent = "Saving…";

    // Send all three keys explicitly so the server can distinguish
    // "key not mentioned" (skip) from "key = empty string" (clear field).
    const { ok, data } = await API.put("/api/profile/", { full_name, phone, address });

    btn.disabled    = false;
    btn.textContent = "Save Changes";

    if (ok) Toast.success("Profile updated!");
    else    Toast.error(data.error || "Could not update profile.");
  });

  const pwForm = document.getElementById("password-form");
  if (pwForm) {
    pwForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const old_password = pwForm.querySelector('[name="old_password"]').value;
      const new_password = pwForm.querySelector('[name="new_password"]').value;
      const btn = pwForm.querySelector('[type="submit"]');
      btn.disabled = true;
      const { ok, data } = await API.post("/api/profile/change-password", { old_password, new_password });
      btn.disabled = false;
      if (ok) { Toast.success("Password changed!"); pwForm.reset(); }
      else    Toast.error(data.error || "Password change failed.");
    });
  }
}

// ─── Cart Page ───────────────────────────────────────────────
function initCartPage() {
  if (!document.getElementById("cart-page")) return;

  document.querySelectorAll("[data-remove-item]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const itemId = btn.dataset.removeItem;
      const { ok } = await Cart.remove(itemId);
      if (ok) location.reload();
    });
  });

  document.querySelectorAll("[data-qty-input]").forEach(input => {
    let debounce;
    input.addEventListener("change", () => {
      clearTimeout(debounce);
      debounce = setTimeout(async () => {
        const itemId = input.dataset.qtyInput;

        // BUG FIX #24: parseInt() on an empty or non-numeric input returns NaN.
        // JSON.stringify(NaN) produces "null", so the server received
        // {"quantity": null} → int(None) → TypeError 500.
        // Now we validate before making the call.
        const qty = parseInt(input.value, 10);
        if (isNaN(qty) || qty < 0) {
          Toast.error("Please enter a valid quantity.");
          return;
        }
        const { ok } = await Cart.update(itemId, qty);
        if (ok) location.reload();
      }, 400);
    });
  });

  const promoBtn = document.getElementById("apply-promo");
  if (promoBtn) {
    promoBtn.addEventListener("click", async () => {
      const code = document.getElementById("promo-input")?.value.trim().toUpperCase();
      if (!code) { Toast.info("Enter a promo code."); return; }

      promoBtn.disabled    = true;
      promoBtn.textContent = "Applying…";

      const { ok, data } = await API.post("/api/cart/promo", { code });

      promoBtn.disabled    = false;
      promoBtn.textContent = "Apply";

      if (ok) {
        Toast.success(`Code applied! You save ₹${data.discount}`);
        const discountEl = document.getElementById("discount-display");
        if (discountEl) discountEl.textContent = `- ₹${data.discount}`;
        const totalEl = document.getElementById("total-display");
        if (totalEl) totalEl.textContent = `₹${data.new_total}`;
        // Store the applied code so checkout can pick it up
        if (promoBtn.dataset) promoBtn.dataset.appliedCode = code;
      } else {
        Toast.error(data.error || "Invalid promo code.");
      }
    });
  }

  const checkoutBtn = document.getElementById("checkout-btn");
  if (checkoutBtn) {
    checkoutBtn.addEventListener("click", async () => {
      const address = document.getElementById("shipping-address")?.value.trim();
      const code    = document.getElementById("promo-input")?.value.trim().toUpperCase() || "";
      if (!address) { Toast.error("Please enter your shipping address."); return; }

      checkoutBtn.disabled    = true;
      checkoutBtn.textContent = "Placing order…";

      const { ok, data } = await API.post("/api/cart/checkout", {
        shipping_address: address,
        promo_code: code,
      });

      checkoutBtn.disabled    = false;
      checkoutBtn.textContent = "Place Order";

      if (ok) {
        Toast.success(`Order #${data.order.id} placed! Earned ${data.points_earned} points 🌿`);
        setTimeout(() => { window.location.href = "/order-history"; }, 2000);
      } else {
        Toast.error(data.error || "Checkout failed. Please try again.");
      }
    });
  }
}

// ─── Favorites Page ──────────────────────────────────────────
function initFavoritesPage() {
  document.querySelectorAll("[data-remove-fav]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const productId = btn.dataset.removeFav;
      const { ok, data } = await API.delete(`/api/favorites/${productId}`);
      if (ok) {
        Toast.success("Removed from favorites.");
        btn.closest("[data-fav-card]")?.remove();
      } else {
        Toast.error(data.error || "Could not remove.");
      }
    });
  });
}

// ─── Product Cards (add-to-cart / favorite buttons) ──────────
function initProductCards() {
  document.querySelectorAll("[data-add-to-cart]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.addToCart, 10);
      Cart.add(id, 1, btn);
    });
  });

  document.querySelectorAll("[data-toggle-fav]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.toggleFav, 10);
      Favorites.toggle(id, btn);
    });
  });
}

// ─── Boot ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initLoginForm();
  initSignupForm();
  initContactForm();
  initLogoutButtons();
  initProfileForm();
  initCartPage();
  initFavoritesPage();
  initProductCards();
});
