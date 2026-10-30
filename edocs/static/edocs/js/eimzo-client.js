/**
 * django-edocs E-IMZO Browser Client
 * Seamless adapter bridging E-IMZO official WebSocket protocol (port 64646 / 64443)
 * with the django-edocs backend APIs.
 */
(function (global) {
  'use strict';

  var EImzoClient = {
    /**
     * Checks if local E-IMZO desktop application is running.
     * Connects via official CAPIWS WebSocket on port 64646 (http) or 64443 (https).
     */
    checkAgent: function () {
      return new Promise(function (resolve) {
        if (typeof EIMZOClient === 'undefined' || typeof CAPIWS === 'undefined') {
          resolve(false);
          return;
        }

        // Ensure default API keys for localhost / 127.0.0.1
        if (!EIMZOClient.API_KEYS) {
          EIMZOClient.API_KEYS = [];
        }
        var defaultKeys = [
          'localhost', '96D0C1491615C82B9A54D9989779DF825B690748224C2B04F500F370D51827CE2644D8D4A82C18184D73AB8530BB8ED537269603F61DB0D03D2104ABF789970B',
          '127.0.0.1', 'A7BCFA5D490B351BE0754130DF03A068F855DB4333D43921125B9CF2670EF6A40370C646B90401955E1F7BC9CDBF59CE0B2C5467D820BE189C845D0B79CFC96F',
          'null', 'E0A205EC4E7B78BBB56AFF83A733A1BB9FD39D562E67978CC5E7D73B0951DB1954595A20672A63332535E13CC6EC1E1FC8857BB09E0855D7E76E411B6FA16E9D'
        ];
        defaultKeys.forEach(function (k) {
          if (EIMZOClient.API_KEYS.indexOf(k) === -1) {
            EIMZOClient.API_KEYS.push(k);
          }
        });

        EIMZOClient.checkVersion(function (major, minor) {
          EIMZOClient.installApiKeys(function () {
            resolve(true);
          }, function (e, r) {
            // Even if custom hostname apikey warning, agent is running
            resolve(true);
          });
        }, function (e, r) {
          resolve(false);
        });
      });
    },

    /**
     * Lists all available E-IMZO certificates from connected tokens and PFX files.
     */
    listCertificates: function () {
      return new Promise(function (resolve, reject) {
        if (typeof EIMZOClient === 'undefined') {
          reject(new Error('EIMZOClient kutubxonasi yuklanmagan.'));
          return;
        }

        EIMZOClient.listAllUserKeys(
          function (vo, rec) {
            return 'key_' + rec + '_' + (vo.serialNumber || rec);
          },
          function (itemId, vo) {
            vo._itemId = itemId;
            return vo;
          },
          function (items, firstId) {
            resolve(items || []);
          },
          function (e, r) {
            reject(new Error(r || 'Sertifikatlarni yuklab bo\'lmadi'));
          }
        );
      });
    },

    /**
     * Loads a key into E-IMZO memory (prompts user for password if needed).
     */
    loadKey: function (certItem) {
      return new Promise(function (resolve, reject) {
        if (typeof EIMZOClient === 'undefined') {
          reject(new Error('EIMZOClient yuklanmagan'));
          return;
        }
        EIMZOClient.loadKey(certItem, function (keyId) {
          resolve(keyId);
        }, function (e, r) {
          reject(new Error(r || 'Kalitni yuklab bo\'lmadi'));
        }, true);
      });
    },

    /**
     * Creates an attached PKCS#7 signature over the given challenge base64 string.
     */
    createPkcs7: function (keyId, dataBase64) {
      return new Promise(function (resolve, reject) {
        EIMZOClient.createPkcs7(keyId, dataBase64, null, function (pkcs7) {
          resolve(pkcs7);
        }, function (e, r) {
          reject(new Error(r || 'PKCS#7 imzo yaratishda xatolik'));
        }, false, true); // detached=false, isDataBase64Encoded=true
      });
    },

    /**
     * Full signing helper: fetches challenge, loads key, creates PKCS#7, and posts to django-edocs backend.
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

          var challengeData = challengeRes.challenge;

          // 2. Load key
          return self.loadKey(certItem).then(function (keyId) {
            // 3. Create PKCS#7 attached signature
            return self.createPkcs7(keyId, challengeData).then(function (pkcs7) {
              // 4. Send PKCS#7 to django-edocs backend
              return fetch(baseUrl + guid + '/sign/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                  'X-CSRFToken': self.getCsrfToken()
                },
                body: JSON.stringify({
                  pkcs7: pkcs7,
                  certificate_info: {
                    serialNumber: certItem.serialNumber || '',
                    CN: certItem.CN || '',
                    TIN: certItem.TIN || '',
                    PINFL: certItem.PINFL || '',
                    UID: certItem.UID || '',
                    O: certItem.O || '',
                    validFrom: (certItem.validFrom instanceof Date) ? certItem.validFrom.toISOString() : (certItem.validFrom || ''),
                    validTo: (certItem.validTo instanceof Date) ? certItem.validTo.toISOString() : (certItem.validTo || ''),
                    type: certItem.type || 'pfx'
                  }
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
