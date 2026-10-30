/**
 * django-edocs E-IMZO Browser Client
 * Provides seamless integration with the local E-IMZO agent (port 64443).
 */
(function (global) {
  'use strict';

  var EIMZO_URL = 'http://127.0.0.1:64443/site/';

  function postToAgent(plugin, name, data) {
    var url = EIMZO_URL + (plugin ? plugin + '/' : '') + name;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: data ? new URLSearchParams(data).toString() : ''
    }).then(function (res) {
      return res.json();
    });
  }

  var EImzoClient = {
    /**
     * Checks if local E-IMZO application is running.
     */
    checkAgent: function () {
      return fetch(EIMZO_URL, { method: 'GET' })
        .then(function () { return true; })
        .catch(function () { return false; });
    },

    /**
     * Lists all available E-IMZO certificates from connected tokens/files.
     */
    listCertificates: function () {
      return postToAgent('pfx', 'list_all_certificates').then(function (res) {
        if (!res || !res.success) {
          throw new Error(res ? res.reason : 'Sertifikatlarni yuklab bo\'lmadi');
        }
        return res.certificates || [];
      });
    },

    /**
     * Loads a key into memory by path/disk using user password.
     */
    loadKey: function (certItem) {
      return postToAgent('pfx', 'load_key', {
        disk: certItem.disk,
        path: certItem.path,
        name: certItem.name,
        alias: certItem.alias
      }).then(function (res) {
        if (!res || !res.success) {
          throw new Error(res ? res.reason : 'Kalitni yuklab bo\'lmadi');
        }
        return res.keyId;
      });
    },

    /**
     * Creates a PKCS#7 detached/attached signature over given challenge string.
     */
    createPkcs7: function (keyId, dataBase64) {
      return postToAgent('pkcs7', 'create_pkcs7', {
        keyId: keyId,
        data: dataBase64,
        timestamper: ''
      }).then(function (res) {
        if (!res || !res.success) {
          throw new Error(res ? res.reason : 'PKCS#7 imzo yaratishda xatolik');
        }
        return res.pkcs7_64;
      });
    },

    /**
     * Full signing helper: fetches challenge, loads key, signs, and posts to django-edocs backend.
     */
    signDocument: function (guid, certItem, apiBaseUrl) {
      var self = this;
      var baseUrl = (apiBaseUrl || '/api/edocs/').replace(/\/$/, '') + '/';

      // 1. Get challenge
      return fetch(baseUrl + guid + '/challenge/', {
        headers: { 'Accept': 'application/json' }
      })
        .then(function (res) { return res.json(); })
        .then(function (challengeRes) {
          if (!challengeRes.success) {
            throw new Error(challengeRes.message || 'Challenge olishda xatolik');
          }

          // 2. Load key
          return self.loadKey(certItem).then(function (keyId) {
            // 3. Create PKCS#7
            return self.createPkcs7(keyId, challengeRes.challenge).then(function (pkcs7) {
              // 4. Send PKCS#7 to backend
              return fetch(baseUrl + guid + '/sign/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                  'X-CSRFToken': self.getCsrfToken()
                },
                body: JSON.stringify({
                  pkcs7: pkcs7,
                  certificate_info: certItem
                })
              }).then(function (r) { return r.json(); });
            });
          });
        });
    },

    getCsrfToken: function () {
      var match = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
      return match ? match[2] : '';
    }
  };

  global.EImzoClient = EImzoClient;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = EImzoClient;
  }
})(typeof window !== 'undefined' ? window : this);
