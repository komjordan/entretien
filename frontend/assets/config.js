/* Le service d'origine attend un POST multipart : cv, entreprise, offre, format.
   Sur entretien.komjordan.fr, conserver /api/generate et le backend existant.
   Ne jamais placer de clé Anthropic ou autre secret dans ce fichier. */
window.ENT_CONFIG = Object.freeze({
  apiUrl: '/api/generate',
  timeoutMs: 120000,
  maxFileBytes: 5 * 1024 * 1024
});
