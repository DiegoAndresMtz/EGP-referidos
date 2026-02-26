import aiosmtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import get_settings

logger = logging.getLogger(__name__)


def _build_payment_date_html(
    referidor_name: str,
    lead_name: str,
    payment_date_str: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>¡Felicitaciones!</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f1fb; font-family:'Segoe UI', Arial, sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1fb; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px; width:100%; background:#ffffff;
                      border-radius:20px; overflow:hidden;
                      box-shadow: 0 8px 32px rgba(139,92,246,0.13);">

          <!-- Header con confeti visual -->
          <tr>
            <td style="background: linear-gradient(135deg, #5b21b6 0%, #7c3aed 50%, #a855f7 100%);
                       padding: 48px 40px 36px; text-align:center;">
              <div style="font-size:52px; margin-bottom:12px; line-height:1;">🏆</div>
              <h1 style="margin:0 0 8px; color:#ffffff; font-size:30px; font-weight:800;
                         letter-spacing:-0.5px; text-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                ¡Felicitaciones, {referidor_name}!
              </h1>
              <p style="margin:0; color:rgba(255,255,255,0.90); font-size:16px; font-weight:400;">
                Tu esfuerzo está dando resultados increíbles 🌟
              </p>
            </td>
          </tr>

          <!-- Mensaje principal -->
          <tr>
            <td style="padding: 36px 40px 0;">
              <p style="margin:0 0 8px; color:#1f2937; font-size:17px; line-height:1.75;">
                Hola <strong style="color:#7c3aed;">{referidor_name}</strong>, tenemos una
                <strong>excelente noticia</strong> para ti. 🎊
              </p>
              <p style="margin:0 0 24px; color:#374151; font-size:16px; line-height:1.75;">
                La persona que referiste, <strong style="color:#7c3aed; font-size:17px;">{lead_name}</strong>,
                ha confirmado la fecha en que realizará el pago de su
                <strong>cuota inicial</strong> para adquirir su vivienda con EGP Construcciones.
                ¡Esto significa que tu recomendación está a punto de convertirse en una venta exitosa!
              </p>
            </td>
          </tr>

          <!-- Caja destacada: quién paga y cuándo -->
          <tr>
            <td style="padding: 0 40px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background: linear-gradient(135deg, #faf5ff 0%, #ede9fe 100%);
                            border: 2px solid #c4b5fd;
                            border-radius: 16px;">
                <tr>
                  <td style="padding: 28px 32px;">

                    <!-- Quién -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                      <tr>
                        <td style="width:40px; vertical-align:middle;">
                          <div style="font-size:28px;">👤</div>
                        </td>
                        <td style="vertical-align:middle; padding-left:12px;">
                          <p style="margin:0 0 2px; color:#6d28d9; font-size:11px; font-weight:700;
                                     text-transform:uppercase; letter-spacing:1px;">Persona que pagará</p>
                          <p style="margin:0; color:#3b0764; font-size:20px; font-weight:800;">
                            {lead_name}
                          </p>
                        </td>
                      </tr>
                    </table>

                    <!-- Divisor -->
                    <hr style="border:none; border-top:1px solid #c4b5fd; margin:0 0 20px;" />

                    <!-- Cuándo -->
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="width:40px; vertical-align:middle;">
                          <div style="font-size:28px;">📅</div>
                        </td>
                        <td style="vertical-align:middle; padding-left:12px;">
                          <p style="margin:0 0 2px; color:#6d28d9; font-size:11px; font-weight:700;
                                     text-transform:uppercase; letter-spacing:1px;">Fecha acordada de pago</p>
                          <p style="margin:0; color:#3b0764; font-size:22px; font-weight:800;">
                            {payment_date_str}
                          </p>
                        </td>
                      </tr>
                    </table>

                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Mensaje motivacional -->
          <tr>
            <td style="padding: 0 40px 32px;">
              <p style="margin:0 0 16px; color:#374151; font-size:15px; line-height:1.75;">
                Esto es fruto de tu confianza en nosotros y del valor que le transmitiste
                a <strong>{lead_name}</strong>. El equipo de EGP Construcciones estará
                acompañando cada paso de este proceso para garantizar la mejor experiencia.
              </p>
              <p style="margin:0 0 28px; color:#374151; font-size:15px; line-height:1.75;">
                Puedes revisar el estado de todos tus referidos desde tu panel en cualquier momento.
              </p>

              <!-- CTA -->
              <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                <tr>
                  <td align="center"
                      style="background: linear-gradient(135deg, #6d28d9, #a855f7);
                             border-radius:12px;
                             box-shadow: 0 4px 14px rgba(109,40,217,0.35);">
                    <a href="/dashboard/referidor"
                       style="display:inline-block; padding:15px 36px;
                              color:#ffffff; font-size:15px; font-weight:700;
                              text-decoration:none; letter-spacing:0.4px;">
                      Ver mis referidos &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding: 0 40px;">
              <hr style="border:none; border-top:1px solid #ede9fe; margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 22px 40px 30px; text-align:center;">
              <p style="margin:0 0 4px; color:#9ca3af; font-size:13px;">
                Mensaje generado automáticamente por <strong>EGP Referidos</strong>.
              </p>
              <p style="margin:0; color:#d1d5db; font-size:12px;">
                Por favor no respondas a este correo.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


async def send_payment_date_notification(
    to_email: str,
    referidor_name: str,
    lead_name: str,
    payment_date_str: str,
) -> None:
    """Send congratulatory email to referidor when advisor sets a payment date."""
    cfg = get_settings()

    if not cfg.EMAILS_ENABLED:
        logger.info("Emails desactivados (EMAILS_ENABLED=false), no se envía.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎉 ¡Tu referido {lead_name} tiene fecha de pago!"
        msg["From"] = cfg.SMTP_FROM
        msg["To"] = to_email

        html_content = _build_payment_date_html(referidor_name, lead_name, payment_date_str)
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=cfg.SMTP_HOST,
            port=cfg.SMTP_PORT,
            username=cfg.SMTP_USER,
            password=cfg.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Email enviado a {to_email} para lead {lead_name}")
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {type(e).__name__}: {e}")
