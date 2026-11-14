function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  sidebar.classList.toggle("active");
  overlay.classList.toggle("active");
}

document.addEventListener('DOMContentLoaded', () => {
  // Attach toggle to hamburger click.
  // (Done after the page loads: sidebar.html is included before navbar.html,
  //  so the hamburger button doesn't exist yet when this file first runs.)
  const hamburger = document.getElementById("hamburger");
  if (hamburger) {
    hamburger.addEventListener("click", toggleSidebar);
  }

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
