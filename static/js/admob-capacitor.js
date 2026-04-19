window.ADS = (() => {
  let admobInstance = null;
  let initialized = false;
  let bannerVisible = false;
  let interstitialReady = false;

  const TEST_BANNER_ID = 'ca-app-pub-3940256099942544/9214589741';
  const TEST_INTERSTITIAL_ID = 'ca-app-pub-3940256099942544/1033173712';

  const isNativeAndroid = () =>
    !!window.Capacitor &&
    typeof window.Capacitor.getPlatform === 'function' &&
    window.Capacitor.getPlatform() === 'android';

  function getAdMob() {
    if (admobInstance) return admobInstance;

    try {
      if (window.Capacitor?.Plugins?.AdMob) {
        admobInstance = window.Capacitor.Plugins.AdMob;
        return admobInstance;
      }

      if (typeof window.Capacitor?.registerPlugin === 'function') {
        admobInstance = window.Capacitor.registerPlugin('AdMob');
        return admobInstance;
      }
    } catch (err) {
      console.error('No se pudo obtener el plugin AdMob:', err);
    }

    return null;
  }

  async function initAds() {
    if (!isNativeAndroid()) {
      console.log('ADS: no es Android nativo, se omite AdMob');
      return false;
    }

    const AdMob = getAdMob();
    if (!AdMob) {
      console.error('ADS: plugin AdMob no disponible');
      return false;
    }

    if (initialized) return true;

    try {
      console.log('ADS: inicializando AdMob...');
      await AdMob.initialize();

      let consentInfo = null;
      try {
        consentInfo = await AdMob.requestConsentInfo();
        console.log('ADS: consentInfo', consentInfo);

        if (consentInfo && !consentInfo.canRequestAds && consentInfo.isConsentFormAvailable) {
          consentInfo = await AdMob.showConsentForm();
          console.log('ADS: consentimiento actualizado', consentInfo);
        }
      } catch (consentError) {
        console.warn('ADS: fallo al gestionar consentimiento, se continúa:', consentError);
      }

      initialized = true;
      console.log('ADS: AdMob inicializado correctamente');
      return true;
    } catch (e) {
      console.error('ADS: error en initialize()', e);
      return false;
    }
  }

  async function showBottomBanner() {
    if (!isNativeAndroid()) return false;

    const AdMob = getAdMob();
    if (!AdMob) {
      console.error('ADS: showBottomBanner sin plugin AdMob');
      return false;
    }

    const ok = await initAds();
    if (!ok) return false;

    try {
      if (bannerVisible) {
        console.log('ADS: banner ya visible');
        return true;
      }

      console.log('ADS: mostrando banner...');
      await AdMob.showBanner({
        adId: TEST_BANNER_ID,
        adSize: 'BANNER',
        position: 'BOTTOM_CENTER',
        margin: 0,
        isTesting: true
      });

      bannerVisible = true;
      document.body.classList.add('admob-banner-active');
      console.log('ADS: banner mostrado');
      return true;
    } catch (e) {
      bannerVisible = false;
      document.body.classList.remove('admob-banner-active');
      console.error('ADS: error al mostrar banner', e);
      return false;
    }
  }

  async function hideBanner() {
    if (!isNativeAndroid()) return false;

    const AdMob = getAdMob();
    if (!AdMob) return false;

    try {
      await AdMob.hideBanner();
      bannerVisible = false;
      document.body.classList.remove('admob-banner-active');
      console.log('ADS: banner ocultado');
      return true;
    } catch (e) {
      console.error('ADS: error al ocultar banner', e);
      return false;
    }
  }

  async function prepareInterstitial() {
    if (!isNativeAndroid()) return false;

    const AdMob = getAdMob();
    if (!AdMob) {
      console.error('ADS: prepareInterstitial sin plugin AdMob');
      return false;
    }

    const ok = await initAds();
    if (!ok) return false;

    try {
      console.log('ADS: preparando interstitial...');
      await AdMob.prepareInterstitial({
        adId: TEST_INTERSTITIAL_ID,
        isTesting: true
      });
      interstitialReady = true;
      console.log('ADS: interstitial preparado');
      return true;
    } catch (e) {
      interstitialReady = false;
      console.error('ADS: error al preparar interstitial', e);
      return false;
    }
  }

  async function showInterstitial() {
    if (!isNativeAndroid()) return false;

    const AdMob = getAdMob();
    if (!AdMob) {
      console.error('ADS: showInterstitial sin plugin AdMob');
      return false;
    }

    if (!interstitialReady) {
      const prepared = await prepareInterstitial();
      if (!prepared) return false;
    }

    try {
      console.log('ADS: mostrando interstitial...');
      await AdMob.showInterstitial();
      interstitialReady = false;

      // Lo dejamos listo para la próxima
      prepareInterstitial().catch((e) => {
        console.warn('ADS: no se pudo precargar el siguiente interstitial', e);
      });

      console.log('ADS: interstitial mostrado');
      return true;
    } catch (e) {
      interstitialReady = false;
      console.error('ADS: error al mostrar interstitial', e);
      return false;
    }
  }

  function debugStatus() {
    return {
      isNativeAndroid: isNativeAndroid(),
      hasCapacitor: !!window.Capacitor,
      hasPluginsObject: !!window.Capacitor?.Plugins,
      hasAdMobPlugin: !!window.Capacitor?.Plugins?.AdMob,
      initialized,
      bannerVisible,
      interstitialReady
    };
  }

  return {
    initAds,
    showBottomBanner,
    hideBanner,
    prepareInterstitial,
    showInterstitial,
    debugStatus
  };
})();