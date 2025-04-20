document.addEventListener("DOMContentLoaded", function () {
  // Общие данные о поведении пользователя
  const behaviorData = {
    keystrokes: [],
    mouseMovements: [],
    device: navigator.userAgent,
    timestamp: null,
  };

  // Сбор нажатий клавиш для всех форм
  document.addEventListener("keydown", function (e) {
    behaviorData.keystrokes.push({
      key: e.key,
      timestamp: Date.now(),
    });
  });

  // Сбор движений мыши
  document.addEventListener("mousemove", function (e) {
    behaviorData.mouseMovements.push({
      x: e.clientX,
      y: e.clientY,
      timestamp: Date.now(),
    });
  });

  // ===== ОБРАБОТКА ВХОДА =====
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const username = document.getElementById("username").value;
      const password = document.getElementById("password").value;

      if (!username || !password) {
        showError("loginError", "Заполните все поля");
        return;
      }

      behaviorData.timestamp = new Date().toISOString();

      try {
        const response = await fetch("/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: username,
            password: password,
            behaviorData: behaviorData,
          }),
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || "Ошибка сервера");
        }

        if (result.success) {
          if (result.requiresMFA) {
            document.getElementById("mfa").style.display = "block";
          } else if (result.redirect) {
            window.location.href = result.redirect;
          }
        } else {
          showError("loginError", result.error || "Ошибка входа");
        }
      } catch (error) {
        console.error("Ошибка входа:", error);
        showError(
          "loginError",
          error.message || "Ошибка соединения с сервером"
        );
      }
    });
  }

  // ===== ОБРАБОТКА РЕГИСТРАЦИИ =====
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const formData = {
        username: document.getElementById("username").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirm_password").value,
        security_question: document.getElementById("security_question").value,
        security_answer: document.getElementById("security_answer").value,
        behaviorData: {
          ...behaviorData,
          timestamp: new Date().toISOString(),
        },
      };

      // Валидация
      if (
        !formData.username ||
        !formData.email ||
        !formData.password ||
        !formData.confirm_password ||
        !formData.security_question ||
        !formData.security_answer
      ) {
        showError("registerError", "Все поля обязательны для заполнения");
        return;
      }

      if (formData.password !== formData.confirm_password) {
        showError("registerError", "Пароли не совпадают");
        return;
      }

      try {
        const response = await fetch("/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || "Ошибка регистрации");
        }

        if (result.success) {
          alert(result.message || "Регистрация успешна!");
          if (result.redirect) {
            window.location.href = result.redirect;
          }
        } else {
          showError("registerError", result.error || "Ошибка регистрации");
        }
      } catch (error) {
        console.error("Ошибка регистрации:", error);
        showError("registerError", error.message || "Ошибка при регистрации");
      }
    });
  }

  // ===== ОБРАБОТКА MFA =====
  window.verifyMFA = async function () {
    const code = document.getElementById("mfaCode").value;

    if (!code) {
      showError("mfaError", "Введите код подтверждения");
      return;
    }

    try {
      const response = await fetch("/verify-mfa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code: code }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Ошибка верификации");
      }

      if (result.success && result.redirect) {
        window.location.href = result.redirect;
      } else {
        showError("mfaError", result.error || "Неверный код подтверждения");
      }
    } catch (error) {
      console.error("Ошибка MFA:", error);
      showError("mfaError", error.message || "Ошибка соединения с сервером");
    }
  };

  // Вспомогательная функция для отображения ошибок
  function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.style.display = "block";
      setTimeout(() => {
        errorElement.style.display = "none";
      }, 5000);
    } else {
      alert(message);
    }
  }
});
