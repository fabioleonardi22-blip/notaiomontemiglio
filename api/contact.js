const nodemailer = require('nodemailer');

const MAX = 12000;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Metodo non consentito.' });
  }

  const { GMAIL_USER, GMAIL_APP_PASSWORD } = process.env;
  if (!GMAIL_USER || !GMAIL_APP_PASSWORD) {
    return res.status(503).json({ error: 'Il servizio di invio non è ancora configurato. Contatta direttamente lo Studio.' });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
    // Campo-esca antispam: i visitatori reali lo lasciano vuoto.
    if (body.website) return res.status(200).json({ ok: true });

    const nome = String(body.nome || '').trim().slice(0, 160);
    const email = String(body.email || '').trim().slice(0, 254);
    const telefono = String(body.telefono || '').trim().slice(0, 60);
    const sede = String(body.sede || '').trim().slice(0, 80);
    const argomento = String(body.argomento || '').trim().slice(0, 100);
    const messaggio = String(body.messaggio || '').trim().slice(0, 5000);
    const privacy = body.privacy === true || body.privacy === 'on' || body.privacy === 'true';

    if (!nome || !EMAIL_RE.test(email) || !privacy) {
      return res.status(400).json({ error: 'Controlla nome, indirizzo email e conferma privacy.' });
    }
    if ([nome, email, telefono, sede, argomento, messaggio].some(v => v.length > MAX)) {
      return res.status(400).json({ error: 'La richiesta è troppo lunga.' });
    }

    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: GMAIL_USER,
        pass: GMAIL_APP_PASSWORD.replace(/\s/g, '')
      },
      connectionTimeout: 10000,
      greetingTimeout: 10000,
      socketTimeout: 15000
    });

    const text = [
      'NUOVA RICHIESTA DAL SITO DELLO STUDIO NOTARILE',
      '',
      'Nome e cognome: ' + nome,
      'Email: ' + email,
      'Telefono: ' + (telefono || 'Non indicato'),
      'Sede preferita: ' + (sede || 'Non indicata'),
      'Argomento: ' + (argomento || 'Non indicato'),
      '',
      'Messaggio:',
      messaggio || 'Nessun messaggio aggiuntivo',
      '',
      'La persona ha confermato di aver letto l’informativa privacy.'
    ].join('\n');

    await transporter.sendMail({
      from: { name: 'Studio Notarile Daria Montemiglio', address: GMAIL_USER },
      to: 'dmontemiglio@notariato.it',
      replyTo: email,
      subject: 'Richiesta appuntamento - ' + nome,
      text,
      html: '<h2>Nuova richiesta dal sito</h2>' +
        '<p><strong>Nome:</strong> ' + escapeHtml(nome) + '</p>' +
        '<p><strong>Email:</strong> ' + escapeHtml(email) + '</p>' +
        '<p><strong>Telefono:</strong> ' + escapeHtml(telefono || 'Non indicato') + '</p>' +
        '<p><strong>Sede preferita:</strong> ' + escapeHtml(sede || 'Non indicata') + '</p>' +
        '<p><strong>Argomento:</strong> ' + escapeHtml(argomento || 'Non indicato') + '</p>' +
        '<p><strong>Messaggio:</strong><br>' + escapeHtml(messaggio || 'Nessun messaggio aggiuntivo').replace(/\n/g, '<br>') + '</p>' +
        '<p>La persona ha confermato di aver letto l’informativa privacy.</p>'
    });

    return res.status(200).json({ ok: true });
  } catch (error) {
    // Non registrare dati personali né credenziali nei log.
    console.error('Contact email delivery failed:', error && error.code ? error.code : 'SMTP_ERROR');
    return res.status(502).json({ error: 'Invio non riuscito. Riprova tra qualche minuto oppure contatta lo Studio via email.' });
  }
};
