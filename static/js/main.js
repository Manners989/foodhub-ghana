document.addEventListener('DOMContentLoaded', function () {
  const csrfToken = window.FOODHUB && window.FOODHUB.csrfToken;

  /* ---------- Scroll reveal ---------- */
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('in-view'));
  }

  /* ---------- Update cart badges everywhere ---------- */
  function updateCartBadges(count) {
    document.querySelectorAll('#cart-count, #cart-count-mobile').forEach((el) => {
      el.textContent = count;
      el.classList.add('bump');
      setTimeout(() => el.classList.remove('bump'), 250);
    });
  }

  function showToast(message, ok = true) {
    const stack = document.querySelector('.toast-stack') || (() => {
      const div = document.createElement('div');
      div.className = 'toast-stack';
      document.body.appendChild(div);
      return div;
    })();
    const alert = document.createElement('div');
    alert.className = `alert alert-${ok ? 'success' : 'danger'} alert-dismissible fade show shadow-sm animate__animated animate__fadeInRight`;
    alert.role = 'alert';
    alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    stack.appendChild(alert);
    setTimeout(() => alert.remove(), 3500);
  }

  /* ---------- AJAX add to cart ---------- */
  document.querySelectorAll('form.ajax-add-form').forEach((form) => {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      const originalHtml = btn ? btn.innerHTML : null;
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
      }
      fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: new FormData(form),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            updateCartBadges(data.cart.count);
            showToast(data.message || 'Added to cart!');
          } else {
            showToast(data.message || 'Something went wrong.', false);
          }
        })
        .catch(() => showToast('Network error. Please try again.', false))
        .finally(() => {
          if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
          }
        });
    });
  });

  /* ---------- Newsletter AJAX ---------- */
  const newsletterForm = document.getElementById('newsletter-form');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', function (e) {
      e.preventDefault();
      fetch(newsletterForm.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken },
        body: new FormData(newsletterForm),
      })
        .then((r) => r.json())
        .then((data) => {
          showToast(data.message, data.ok);
          if (data.ok) newsletterForm.reset();
        })
        .catch(() => showToast('Network error. Please try again.', false));
    });
  }

  /* ---------- Quantity selectors (detail page) ---------- */
  document.querySelectorAll('.qty-selector').forEach((selector) => {
    const input = selector.querySelector('input');
    selector.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', () => {
        let val = parseInt(input.value || '1', 10);
        val = btn.dataset.action === 'inc' ? val + 1 : Math.max(1, val - 1);
        input.value = val;
        input.dispatchEvent(new Event('change'));
      });
    });
  });

  /* ---------- Cart page: quantity update via AJAX ---------- */
  document.querySelectorAll('.cart-qty-form').forEach((form) => {
    const input = form.querySelector('input[name="quantity"]');
    const submitUpdate = () => {
      fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken },
        body: new FormData(form),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) window.location.reload();
        });
    };
    form.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        let val = parseInt(input.value || '1', 10);
        val = btn.dataset.action === 'inc' ? val + 1 : val - 1;
        input.value = Math.max(0, val);
        submitUpdate();
      });
    });
  });

  /* ---------- Delivery type toggling on checkout ---------- */
  const deliveryRadios = document.querySelectorAll('input[name="delivery_type"], select[name="delivery_type"]');
  const addressBlock = document.getElementById('address-block');
  function toggleAddressBlock() {
    const select = document.querySelector('select[name="delivery_type"]');
    if (!select || !addressBlock) return;
    addressBlock.style.display = select.value === 'delivery' ? 'block' : 'none';
  }
  const deliverySelect = document.querySelector('select[name="delivery_type"]');
  if (deliverySelect) {
    deliverySelect.addEventListener('change', toggleAddressBlock);
    toggleAddressBlock();
  }

  /* ---------- Payment method toggling on checkout ---------- */
  const momoBlock = document.getElementById('momo-block');
  const momoCardNote = document.getElementById('momo-card-note');
  const paymentSelect = document.querySelector('select[name="payment_method"]');
  function toggleMomoBlock() {
    if (!paymentSelect) return;
    if (momoBlock) momoBlock.style.display = paymentSelect.value === 'momo' ? 'block' : 'none';
    if (momoCardNote) momoCardNote.style.display = (paymentSelect.value === 'momo' || paymentSelect.value === 'card') ? 'block' : 'none';
  }
  if (paymentSelect) {
    paymentSelect.addEventListener('change', toggleMomoBlock);
    toggleMomoBlock();
  }

  /* ---------- Star rating input on review form ---------- */
  document.querySelectorAll('.star-rating-picker').forEach((picker) => {
    const stars = picker.querySelectorAll('i');
    const select = picker.parentElement.querySelector('select[name="rating"]');
    stars.forEach((star) => {
      star.addEventListener('click', () => {
        const val = star.dataset.value;
        if (select) select.value = val;
        stars.forEach((s) => s.classList.toggle('bi-star-fill', s.dataset.value <= val));
        stars.forEach((s) => s.classList.toggle('bi-star', s.dataset.value > val));
      });
    });
  });
});
