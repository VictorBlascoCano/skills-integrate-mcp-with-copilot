document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const loginButton = document.getElementById("teacher-login-button");
  const logoutButton = document.getElementById("teacher-logout-button");
  const sessionLabel = document.getElementById("teacher-session-label");
  const loginDialog = document.getElementById("teacher-login-dialog");
  const loginForm = document.getElementById("teacher-login-form");
  const loginError = document.getElementById("teacher-login-error");
  let teacherToken = sessionStorage.getItem("teacherToken");
  let teacherUsername = "";

  function authHeaders() {
    return teacherToken ? { Authorization: `Bearer ${teacherToken}` } : {};
  }

  function syncTeacherControls() {
    const isTeacher = Boolean(teacherToken);
    signupContainer.hidden = !isTeacher;
    loginButton.hidden = isTeacher;
    logoutButton.hidden = !isTeacher;
    sessionLabel.hidden = !isTeacher;
    sessionLabel.textContent = isTeacher ? `Signed in as ${teacherUsername}` : "";
    document.querySelectorAll(".delete-btn").forEach((button) => {
      button.hidden = !isTeacher;
    });
  }

  function clearTeacherSession() {
    teacherToken = "";
    teacherUsername = "";
    sessionStorage.removeItem("teacherToken");
    syncTeacherControls();
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => `<li>
                      <span class="participant-email">${escapeHtml(email)}</span>
                      ${teacherToken ? `<button class="delete-btn" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" aria-label="Unregister ${escapeHtml(email)}">Remove</button>` : ""}
                    </li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        if (response.status === 401) clearTeacherSession();
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        if (response.status === 401) clearTeacherSession();
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  loginButton.addEventListener("click", () => {
    loginError.textContent = "";
    loginError.classList.add("hidden");
    loginForm.reset();
    loginDialog.showModal();
  });

  document.getElementById("teacher-login-cancel").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    loginError.textContent = "";
    loginError.classList.add("hidden");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to sign in");

      teacherToken = result.access_token;
      teacherUsername = result.username;
      sessionStorage.setItem("teacherToken", teacherToken);
      syncTeacherControls();
      loginDialog.close();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = error.message || "Unable to sign in. Please try again.";
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST", headers: authHeaders() });
    } finally {
      clearTeacherSession();
      await fetchActivities();
    }
  });

  async function initializeApp() {
    if (teacherToken) {
      try {
        const response = await fetch("/auth/session", { headers: authHeaders() });
        if (response.ok) {
          const session = await response.json();
          teacherUsername = session.username;
        } else {
          clearTeacherSession();
        }
      } catch {
        clearTeacherSession();
      }
    }
    syncTeacherControls();
    await fetchActivities();
  }

  initializeApp();
});
