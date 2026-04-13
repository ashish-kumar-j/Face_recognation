(function () {
  const FaceApp = {
    ws: null,
    interval: null,

    csrfToken() {
      const m = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : "";
    },

    async api(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (!["GET", "HEAD"].includes((options.method || "GET").toUpperCase())) {
        headers.set("X-CSRF-Token", this.csrfToken());
      }
      if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
      }
      const res = await fetch(path, { credentials: "include", ...options, headers });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      return data;
    },

    async initLoginPage() {
      const form = document.getElementById("login-form");
      const registerBtn = document.getElementById("register-btn");
      const msg = document.getElementById("login-msg");

      form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const email = document.getElementById("email").value;
          const password = document.getElementById("password").value;
          await this.api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
          });
          location.reload();
        } catch (err) {
          msg.textContent = err.message;
        }
      });

      registerBtn?.addEventListener("click", async () => {
        try {
          const email = document.getElementById("email").value;
          const password = document.getElementById("password").value;
          await this.api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, role: "admin" }),
          });
          location.reload();
        } catch (err) {
          msg.textContent = err.message;
        }
      });
    },

    async initDashboard() {
      const video = document.getElementById("live-video");
      const canvas = document.getElementById("capture-canvas");
      const ctx = canvas.getContext("2d");

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
      } catch (err) {
        document.getElementById("live-result").textContent = `Camera error: ${err.message}`;
      }

      document.getElementById("logout-btn")?.addEventListener("click", async () => {
        await this.api("/api/auth/logout", { method: "POST" });
        location.reload();
      });

      document.getElementById("start-live")?.addEventListener("click", () => this.startLive(video, canvas, ctx));
      document.getElementById("stop-live")?.addEventListener("click", () => this.stopLive());

      document.getElementById("add-person")?.addEventListener("click", async () => {
        try {
          const display_name = document.getElementById("person-name").value;
          const external_id = document.getElementById("person-external").value || null;
          await this.api("/api/persons", {
            method: "POST",
            body: JSON.stringify({ display_name, external_id }),
          });
          document.getElementById("person-msg").textContent = "Person added";
          await this.loadPersons();
        } catch (err) {
          document.getElementById("person-msg").textContent = err.message;
        }
      });

      document.getElementById("enroll-camera")?.addEventListener("click", async () => {
        try {
          const personId = Number(document.getElementById("person-select").value);
          const frame = this.captureFrame(video, canvas, ctx);
          await this.api(`/api/persons/${personId}/enroll/camera`, {
            method: "POST",
            body: JSON.stringify({ frame_base64: frame }),
          });
          document.getElementById("person-msg").textContent = "Camera enrollment successful";
        } catch (err) {
          document.getElementById("person-msg").textContent = err.message;
        }
      });

      document.getElementById("enroll-upload")?.addEventListener("click", async () => {
        try {
          const personId = Number(document.getElementById("person-select").value);
          const file = document.getElementById("upload-file").files[0];
          if (!file) {
            throw new Error("Select an image file first");
          }
          const form = new FormData();
          form.append("file", file);
          await this.api(`/api/persons/${personId}/enroll/upload`, { method: "POST", body: form });
          document.getElementById("person-msg").textContent = "Upload enrollment successful";
        } catch (err) {
          document.getElementById("person-msg").textContent = err.message;
        }
      });

      document.getElementById("deactivate-person")?.addEventListener("click", async () => {
        try {
          const personId = Number(document.getElementById("person-select").value);
          await this.api(`/api/persons/${personId}`, { method: "DELETE" });
          await this.loadPersons();
          document.getElementById("person-msg").textContent = "Person deactivated";
        } catch (err) {
          document.getElementById("person-msg").textContent = err.message;
        }
      });

      document.getElementById("refresh-events")?.addEventListener("click", () => this.loadEvents());
      document.getElementById("save-settings")?.addEventListener("click", () => this.saveSettings());
      document.getElementById("refresh-outbox")?.addEventListener("click", () => this.loadOutbox());

      await this.loadPersons();
      await this.loadEvents();
      await this.loadOutbox();
    },

    captureFrame(video, canvas, ctx) {
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.9);
    },

    startLive(video, canvas, ctx) {
      if (this.ws) {
        return;
      }
      const proto = location.protocol === "https:" ? "wss" : "ws";
      this.ws = new WebSocket(`${proto}://${location.host}/api/recognition/live`);

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const text = `${data.match_status} | score=${data.score ?? "n/a"} | liveness=${data.liveness_score ?? "n/a"} | ${data.person_name ?? ""}`;
        document.getElementById("live-result").textContent = text;
      };

      this.ws.onclose = () => {
        this.stopLive();
      };

      this.interval = setInterval(() => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
          return;
        }
        const frame = this.captureFrame(video, canvas, ctx);
        this.ws.send(JSON.stringify({ frame_base64: frame }));
      }, 1200);
    },

    stopLive() {
      if (this.interval) {
        clearInterval(this.interval);
        this.interval = null;
      }
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
    },

    async loadPersons() {
      const select = document.getElementById("person-select");
      if (!select) return;
      const persons = await this.api("/api/persons");
      select.innerHTML = "";
      for (const person of persons) {
        const opt = document.createElement("option");
        opt.value = person.id;
        opt.textContent = `${person.display_name} (#${person.id})`;
        select.appendChild(opt);
      }
    },

    async loadEvents() {
      const body = document.getElementById("events-body");
      if (!body) return;
      const events = await this.api("/api/recognition/events");
      body.innerHTML = events
        .map(
          (e) => `<tr><td>${e.id}</td><td>${e.match_status}</td><td>${e.score ?? "-"}</td><td>${e.person_id ?? "-"}</td><td>${new Date(e.created_at).toLocaleString()}</td></tr>`,
        )
        .join("");
    },

    async saveSettings() {
      try {
        const payload = {
          webhook_url: document.getElementById("webhook-url").value || null,
          webhook_secret: document.getElementById("webhook-secret").value || null,
          strict_match_threshold: Number(document.getElementById("threshold").value || 0.82),
          store_unknown_snapshots: document.getElementById("store-unknown").checked,
        };
        await this.api("/api/settings/webhook", {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        document.getElementById("settings-msg").textContent = "Settings saved";
      } catch (err) {
        document.getElementById("settings-msg").textContent = err.message;
      }
    },

    async loadOutbox() {
      const body = document.getElementById("outbox-body");
      if (!body) return;
      const rows = await this.api("/api/webhook/outbox");
      body.innerHTML = rows
        .map(
          (r) =>
            `<tr><td>${r.id}</td><td>${r.status}</td><td>${r.retry_count}</td><td><button data-retry="${r.id}" class="alt">Retry</button></td></tr>`,
        )
        .join("");

      body.querySelectorAll("button[data-retry]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-retry");
          await this.api(`/api/webhook/outbox/${id}/retry`, { method: "POST" });
          await this.loadOutbox();
        });
      });
    },
  };

  window.FaceApp = FaceApp;
})();
