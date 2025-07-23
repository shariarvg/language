let mediaRecorder, audioChunks = [];
let token = null;

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  const response = await fetch("/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      username,
      password
    })
  });

  const data = await response.json();

  if (data.access_token) {
    token = data.access_token;
    localStorage.setItem("token", data.access_token);
    const token_retrieved = localStorage.getItem("token");
    showWelcomeMessage(token_retrieved);
  } else {
    alert("Login failed.");
  }
});

// ------------------ SIGNUP ------------------
document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = document.getElementById("signup-username").value;
  const password = document.getElementById("signup-password").value;

  const response = await fetch("/signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });

  const data = await response.json();

  if (response.ok) {
    alert("Signup successful! Please log in.");
    document.getElementById("signup-form").reset();
  } else {
    alert("Signup failed: " + (data.detail || "Unknown error"));
  }
});

function showWelcomeMessage(username) {
  document.getElementById("auth-container").style.display = "none";
  const welcomeDiv = document.getElementById("welcome-message");
  welcomeDiv.textContent = `Welcome, ${username}`;
  welcomeDiv.style.display = "block";

  document.getElementById("recording-controls").style.display = "block";
}



async function startRecording() {
  document.getElementById("recording-indicator").style.display = "inline-block";
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = handleUserAudio;
  audioChunks = [];
  mediaRecorder.start();
}

function stopRecording() {
  document.getElementById("recording-indicator").style.display = "none";
  mediaRecorder.stop();
}

async function sendAudioToBackend() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');

  const response = await fetch('/upload-audio', {
    method: 'POST',
    body: formData
  });

  const reader = response.body.getReader();
  const audioContext = new AudioContext();
  let sourceBuffer = audioContext.createBufferSource();
  const stream = new ReadableStream({
    async start(controller) {
      while (true) {
        const { done, value } = await reader.read();
        
        // decode and play streamed audio
        const audioBuffer = await audioContext.decodeAudioData(value.buffer);
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
        if (done) break;
      }
      controller.close();
    }
  });
  
}

async function getGPTResponse() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.webm');

  const response = await fetch('/stream-gpt', {
    method: 'POST',
    body: formData
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const outputDiv = document.getElementById("gpt-output");
  outputDiv.innerText = "";  // Clear previous response

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    outputDiv.innerText += decoder.decode(value, { stream: true });
  }
}

async function handleUserAudio() {
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append("file", audioBlob, "audio.webm");

  // Step 1: Transcribe user audio
  const transcriptResponse = await fetch('/transcribe-audio', {
    method: 'POST',
    body: formData
  });

  const { text: userText } = await transcriptResponse.json();

  // Step 2: Add user message to chat
  const chatContainer = document.getElementById("chat-container");

  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "user-msg";
  userMsgDiv.innerText = userText;
  chatContainer.appendChild(userMsgDiv);

  // Step 3: Create GPT placeholder message
  const gptMsgDiv = document.createElement("div");
  gptMsgDiv.className = "gpt-msg";
  chatContainer.appendChild(gptMsgDiv);

  const gptFeedbackDiv = document.createElement("div");
  gptFeedbackDiv.className = "feedback-msg";
  chatContainer.appendChild(gptFeedbackDiv)

  // Step 4: Stream GPT response
  const gptResponse = await fetch('/continue-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', "Authorization": `Bearer ${token}`},
    body: JSON.stringify({ text: userText })
  });

  const reader = gptResponse.body.getReader();
  const decoder = new TextDecoder("utf-8");

  // Add a span to hold grammar feedback, hidden at first
  const feedbackSpan = document.createElement("span");
  feedbackSpan.className = "grammar-feedback";
  feedbackSpan.style.display = "none";  // Hidden initially
  feedbackSpan.style.color = "red";
  feedbackSpan.style.marginLeft = "6px";
  gptFeedbackDiv.appendChild(feedbackSpan);

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });

    try {
      const maybeJson = JSON.parse(chunk.trim());
      if (maybeJson.scratchpad_update) {
        const flag = document.createElement("span");
        flag.innerText = "⚠️";
        flag.title = "Click to view grammar feedback";
        flag.style.cursor = "pointer";
        flag.style.marginLeft = "8px";

        // On click, reveal feedback next to the emoji
        flag.onclick = () => {
          gptFeedbackDiv.innerText = maybeJson.scratchpad_update;
          gptFeedbackDiv.style.display = "inline";
        };

        gptMsgDiv.appendChild(flag);
        return; // we're done after showing the feedback
      }
    } catch {
      // Not JSON — stream as normal text
    }

    gptMsgDiv.innerText += chunk;
  }

}

async function saveScratchpad(text) {
  await fetch("/scratchpad", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(text)
  });
}

async function loadScratchpad() {
  const res = await fetch("/scratchpad", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  const data = await res.json();
  return data.scratchpad;
}
