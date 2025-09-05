function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  sidebar.classList.toggle("active");
  overlay.classList.toggle("active");
}

// Attach toggle to hamburger click
const hamburger = document.getElementById("hamburger");
if (hamburger) {
  hamburger.addEventListener("click", toggleSidebar);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.has-submenu > a').forEach(link => {
    link.addEventListener('click', e => {
      // only block navigation if it's a toggle (href="#" or empty)
      if (link.getAttribute('href') === '#' || link.getAttribute('href') === '') {
        e.preventDefault();
        link.parentElement.classList.toggle('expanded');
      }
    });
  });
});
