import { useRef, useState } from 'react';
import ApiService from '../services/api';

export const useVoiceRecorder = () => {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState('');
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const start = async () => {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('Voice input is not available in this browser.');
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      return true;
    } catch {
      setError('Microphone permission denied. Continue with text input.');
      return false;
    }
  };

  const stop = async () => {
    const recorder = recorderRef.current;
    if (!recorder) return '';
    return new Promise((resolve) => {
      recorder.onstop = async () => {
        setRecording(false);
        recorder.stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        try {
          const result = await ApiService.transcribeVoice(blob);
          resolve(result.transcript || '');
        } catch {
          setError('Transcription failed. Continue with text input.');
          resolve('');
        }
      };
      recorder.stop();
    });
  };

  return { recording, error, start, stop };
};
