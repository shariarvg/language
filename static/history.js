document.addEventListener("DOMContentLoaded", async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      alert("You must be logged in.");
      window.location.href = "/";
      return;
    }
  
    const listContainer = document.getElementById("conversation-list");
    const detailContainer = document.getElementById("conversation-details");
  
    const res = await fetch("/conversations", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
  
    const conversations = await res.json();
  
    conversations.forEach(conv => {
      const btn = document.createElement("button");
      btn.textContent = `🕑 ${new Date(conv.timestamp).toLocaleString()}`;
      btn.style.display = "block";
      btn.style.margin = "5px";
      btn.onclick = async () => {
        const convRes = await fetch(`/conversations/${conv.id}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        const details = await convRes.json();
        detailContainer.innerHTML = `
          <h3>Scratchpad:</h3>
          <pre>${details.scratchpad.join("\n\n")}</pre>
        `;
      };
      listContainer.appendChild(btn);
    });
  });
  