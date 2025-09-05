document.addEventListener("DOMContentLoaded", function () {
  // ===============================
  // Profile dropdown toggle
  // ===============================
  const userProfile = document.getElementById("userProfile");
  if (userProfile) {
    const profileTrigger = userProfile.querySelector(".profile-dropdown");

    if (profileTrigger) {
      profileTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        userProfile.classList.toggle("active"); // toggle on parent
      });

      // Close dropdown if clicked outside
      document.addEventListener("click", function (e) {
        if (!userProfile.contains(e.target)) {
          userProfile.classList.remove("active");
        }
      });
    }
  }

  // ===============================
  // Sidebar toggle (hamburger + button)
  // ===============================
  const hamburger = document.getElementById("hamburger");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");

  const toggleSidebar = () => {
    if (sidebar) {
      sidebar.classList.toggle("active");
    }
  };

  if (hamburger) hamburger.addEventListener("click", toggleSidebar);
  if (sidebarToggle) sidebarToggle.addEventListener("click", toggleSidebar);

  // Close sidebar when clicking outside
  document.addEventListener("click", function (e) {
    if (
      sidebar &&
      !sidebar.contains(e.target) &&
      (!hamburger || !hamburger.contains(e.target)) &&
      (!sidebarToggle || !sidebarToggle.contains(e.target))
    ) {
      sidebar.classList.remove("active");
    }
  });

  // ===============================
  // Navbar search input (Enter key redirect)
  // ===============================
  const searchInput = document.getElementById("navbarSearchInput");
  if (searchInput) {
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query !== "") {
          window.location.href = `/search/?q=${encodeURIComponent(query)}`;
          searchInput.value = ""; // Clear input after search
        }
      }
    });
  }
});
