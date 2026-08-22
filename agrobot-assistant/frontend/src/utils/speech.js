export const speakText = (text, language = 'en') => {
  if (!('speechSynthesis' in window) || !text) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
  window.speechSynthesis.speak(utterance);
  return true;
};

export const stopSpeaking = () => {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
};
