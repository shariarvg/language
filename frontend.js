let mediaRecorder, audioChunks = [];

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstop = sendAudioToBackend;
  audioChunks = [];
  mediaRecorder.start();
}

function stopRecording() {
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
        if (done) break;
        // decode and play streamed audio
        const audioBuffer = await audioContext.decodeAudioData(value.buffer);
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        source.start();
      }
      controller.close();
    }
  });
}
