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
        mandiPrices: 'Mandi Prices',
        analytics: 'Analytics',
        advisor: 'Advisor',
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
      recommendations: {
        title: 'Crop recommendations', refresh: 'Generate / refresh', generating: 'Generating…',
        coverage: 'AgroBot’s ML model compared your farm against {{count}} trained crop classes. Additional crops are considered only from the verified crop knowledge base.',
        stale: 'Farm information changed after this result. Generate a new recommendation to refresh it.',
        lowReliability: 'Input reliability is low. Treat these results as preliminary.',
        estimatedSoil: 'NPK or pH values were estimated. A soil test can improve reliability.',
        templateFallback: 'Detailed AI explanations are temporarily unavailable. The crop ranking below was generated from the available model and validation rules.',
        partialTemplate: 'Some explanation details were completed with transparent templates. The crop ranking was not changed.',
        noReliableTitle: 'We need more information', noReliableBody: 'AgroBot could not find a sufficiently supported crop recommendation using the available farm information.',
        sourceCombined: 'ML model + crop knowledge', sourceModel: 'ML model', sourceKnowledge: 'Crop knowledge', sourceLegacy: 'Legacy source unknown',
        productScore: 'Product ranking score', dataReliability: 'Data reliability', soilValues: 'Soil values', measured: 'measured', estimated: 'estimated', mainReasons: 'Main reasons', warnings: 'Crop-specific warnings', nextAction: 'Next action', unknown: 'unknown', legacy: 'This older record does not contain source or reliability metadata.', empty: 'No recommendations yet. Complete the questionnaire and generate a plan.',
        inputLimitations: 'Information to improve', improveTitle: 'Improve this recommendation', improveCount: 'Complete {{count}} important farm details.', addSowingDate: 'Add sowing date', addSoilTest: 'Add soil-test values', reviewRainfall: 'Review rainfall information', completeFarmInfo: 'Complete farm information',
        preliminaryTitle: 'Preliminary matches', preliminaryBody: 'These crops may be suitable, but important farm information is missing. Complete the recommended actions before making a planting decision.', preliminarySuitability: 'Suitability: Preliminary',
        verifiedMatches: 'Verified matches', unverifiedChecks: 'Unverified checks', couldNotVerify: 'Could not verify', technicalDetails: 'Technical details', modelVersion: 'Model version', catalogVersion: 'Catalogue version', generationMode: 'Generation mode', modelStatus: 'Model status', modelMatch: 'Model match within supported crops',
        status: { recommended: 'Recommended', preliminary: 'Preliminary', insufficient_support: 'Insufficient support', rejected: 'Rejected' },
        band: { high: 'High suitability', medium: 'Medium suitability', low: 'Low suitability', insufficient_data: 'Insufficient data' },
      },
      pages: {
        advisor: 'Advisor Dashboard',
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
        mandiPrices: 'मंडी भाव',
        analytics: 'विश्लेषण',
        advisor: 'सलाहकार',
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
      recommendations: {
        title: 'फसल सुझाव', refresh: 'बनाएँ / अपडेट करें', generating: 'बन रहा है…',
        coverage: 'AgroBot के ML मॉडल ने आपके खेत की तुलना {{count}} प्रशिक्षित फसल वर्गों से की। अतिरिक्त फसलें केवल सत्यापित फसल ज्ञान से ली जाती हैं।',
        stale: 'इस परिणाम के बाद खेत की जानकारी बदली है। नया सुझाव बनाएँ।',
        lowReliability: 'इनपुट की विश्वसनीयता कम है। इस परिणाम को प्रारंभिक मानें।',
        estimatedSoil: 'NPK या pH का अनुमान लगाया गया है। मिट्टी की जाँच विश्वसनीयता बढ़ा सकती है।',
        templateFallback: 'विस्तृत AI व्याख्या अभी उपलब्ध नहीं है। नीचे की फसल रैंकिंग उपलब्ध मॉडल और सत्यापन नियमों से बनाई गई है।',
        partialTemplate: 'कुछ व्याख्या विवरण पारदर्शी टेम्पलेट से पूरे किए गए। फसल रैंकिंग नहीं बदली गई।',
        noReliableTitle: 'हमें और जानकारी चाहिए', noReliableBody: 'उपलब्ध खेत जानकारी से AgroBot पर्याप्त रूप से समर्थित फसल सुझाव नहीं ढूँढ सका।',
        sourceCombined: 'ML मॉडल + फसल ज्ञान', sourceModel: 'ML मॉडल', sourceKnowledge: 'फसल ज्ञान', sourceLegacy: 'पुराना स्रोत अज्ञात',
        productScore: 'उत्पाद रैंकिंग स्कोर', dataReliability: 'डेटा विश्वसनीयता', soilValues: 'मिट्टी के मान', measured: 'मापे गए', estimated: 'अनुमानित', mainReasons: 'मुख्य कारण', warnings: 'फसल-विशिष्ट चेतावनियाँ', nextAction: 'अगला कदम', unknown: 'अज्ञात', legacy: 'इस पुराने रिकॉर्ड में स्रोत या विश्वसनीयता मेटाडेटा नहीं है।', empty: 'अभी कोई सुझाव नहीं। प्रश्नावली पूरी करके योजना बनाएँ।',
        inputLimitations: 'सुधारने योग्य जानकारी', improveTitle: 'इस सुझाव को बेहतर बनाएँ', improveCount: '{{count}} महत्वपूर्ण खेत विवरण पूरे करें।', addSowingDate: 'बुवाई की तारीख जोड़ें', addSoilTest: 'मिट्टी जाँच के मान जोड़ें', reviewRainfall: 'वर्षा जानकारी देखें', completeFarmInfo: 'खेत की जानकारी पूरी करें',
        preliminaryTitle: 'प्रारंभिक मिलान', preliminaryBody: 'ये फसलें उपयुक्त हो सकती हैं, लेकिन महत्वपूर्ण खेत जानकारी उपलब्ध नहीं है। बुवाई के निर्णय से पहले सुझाए गए विवरण पूरे करें।', preliminarySuitability: 'उपयुक्तता: प्रारंभिक',
        verifiedMatches: 'सत्यापित मिलान', unverifiedChecks: 'असत्यापित जाँच', couldNotVerify: 'सत्यापित नहीं कर सके', technicalDetails: 'तकनीकी विवरण', modelVersion: 'मॉडल संस्करण', catalogVersion: 'कैटलॉग संस्करण', generationMode: 'निर्माण तरीका', modelStatus: 'मॉडल स्थिति', modelMatch: 'समर्थित फसलों में मॉडल मिलान',
        status: { recommended: 'सुझाई गई', preliminary: 'प्रारंभिक', insufficient_support: 'अपर्याप्त समर्थन', rejected: 'अस्वीकृत' },
        band: { high: 'उच्च उपयुक्तता', medium: 'मध्यम उपयुक्तता', low: 'कम उपयुक्तता', insufficient_data: 'अपर्याप्त डेटा' },
      },
      pages: {
        advisor: 'सलाहकार डैशबोर्ड',
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
