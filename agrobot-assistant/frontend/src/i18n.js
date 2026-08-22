import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      nav: {
        dashboard: 'Dashboard',
        crops: 'My Crops',
        weather: 'Weather',
        insights: 'Farm Insights',
        disease: 'Disease Detection',
        questionnaire: 'Update Farm Info',
        schemes: 'Government Schemes',
        analytics: 'Analytics',
        advisor: 'Advisor',
        finance: 'Finance',
        marketplace: 'Marketplace',
        community: 'Community',
        settings: 'Settings',
        logout: 'Logout',
      },
      common: {
        loading: 'Loading...',
        save: 'Save',
        cancel: 'Cancel',
        retry: 'Retry',
        language: 'Language',
        english: 'English',
        hindi: 'Hindi',
        speak: 'Speak',
        listen: 'Listen',
        stop: 'Stop',
      },
      dashboard: {
        title: 'AgroBot Dashboard',
        subtitle: 'Daily farming decisions, alerts, and crop actions in one place',
      },
      pages: {
        advisor: 'Advisor Dashboard',
        finance: 'Financial Tools',
        marketplace: 'Marketplace',
        community: 'Community Forum',
      },
    },
  },
  hi: {
    translation: {
      nav: {
        dashboard: 'डैशबोर्ड',
        crops: 'मेरी फसलें',
        weather: 'मौसम',
        insights: 'खेती जानकारी',
        disease: 'रोग पहचान',
        questionnaire: 'खेत जानकारी अपडेट',
        schemes: 'सरकारी योजनाएं',
        analytics: 'विश्लेषण',
        advisor: 'सलाहकार',
        finance: 'वित्तीय उपकरण',
        marketplace: 'बाज़ार',
        community: 'समुदाय',
        settings: 'सेटिंग्स',
        logout: 'लॉग आउट',
      },
      common: {
        loading: 'लोड हो रहा है...',
        save: 'सहेजें',
        cancel: 'रद्द करें',
        retry: 'फिर प्रयास करें',
        language: 'भाषा',
        english: 'अंग्रेज़ी',
        hindi: 'हिन्दी',
        speak: 'सुनाएं',
        listen: 'बोलें',
        stop: 'रोकें',
      },
      dashboard: {
        title: 'एग्रोबॉट डैशबोर्ड',
        subtitle: 'खेती के दैनिक निर्णय, अलर्ट और फसल कार्य एक जगह',
      },
      pages: {
        advisor: 'सलाहकार डैशबोर्ड',
        finance: 'वित्तीय उपकरण',
        marketplace: 'बाज़ार',
        community: 'समुदाय मंच',
      },
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem('preferred_language') || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
