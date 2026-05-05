"""
Alerting Service — Kirim notifikasi ke Telegram

Dipakai untuk:
- Alert model drift terdeteksi
- Alert error rate tinggi
- Alert server anomali
- Laporan harian otomatis
"""

import httpx
from datetime import datetime
from app.config import settings


class AlertingService:
    """
    Service untuk kirim notifikasi ke Telegram.
    
    Telegram dipilih karena:
    - Gratis
    - API mudah dipakai
    - Notifikasi real-time di smartphone
    - Bisa format pesan dengan Markdown
    """

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def _send(self, text: str) -> bool:
        """
        Kirim pesan ke Telegram.
        
        Pakai parse_mode HTML supaya bisa bold, italic, code formatting.
        timeout=10 detik — kalau gagal, tidak mau nunggu lama.
        """
        if not self.token or not self.chat_id:
            print("⚠️  Telegram tidak dikonfigurasi — skip alert")
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                    }
                )
                return res.json().get("ok", False)
        except Exception as e:
            print(f"⚠️  Telegram alert gagal: {e}")
            return False

    def send_drift_alert(self, feature: str, drift_score: float, threshold: float):
        """Alert ketika model drift terdeteksi."""
        msg = (
            f"🚨 <b>MODEL DRIFT TERDETEKSI</b>\n\n"
            f"📊 Feature: <code>{feature}</code>\n"
            f"📈 Drift Score: <code>{drift_score:.4f}</code>\n"
            f"⚠️  Threshold: <code>{threshold:.4f}</code>\n\n"
            f"Model mungkin perlu di-retrain!\n"
            f"🕐 {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        return self._send(msg)

    def send_daily_report(self, stats: dict):
        """Laporan harian otomatis."""
        msg = (
            f"📋 <b>LAPORAN HARIAN</b>\n"
            f"Credit Risk Platform\n\n"
            f"📥 Total Aplikasi Hari Ini: <b>{stats.get('total_today', 0)}</b>\n"
            f"✅ Disetujui: <b>{stats.get('approved', 0)}</b>\n"
            f"❌ Ditolak: <b>{stats.get('rejected', 0)}</b>\n"
            f"📊 Avg Credit Score: <b>{stats.get('avg_score', 0):.1f}</b>\n"
            f"🎯 Approval Rate: <b>{stats.get('approval_rate', 0):.1f}%</b>\n\n"
            f"🕐 {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        return self._send(msg)

    def send_error_alert(self, error_type: str, detail: str):
        """Alert ketika ada error kritis."""
        msg = (
            f"🔴 <b>ERROR KRITIS</b>\n\n"
            f"Type: <code>{error_type}</code>\n"
            f"Detail: {detail[:200]}\n\n"
            f"🕐 {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        return self._send(msg)

    def send_startup_notice(self):
        """Notifikasi saat server startup."""
        msg = (
            f"🚀 <b>Server Started</b>\n"
            f"Credit Risk Platform online!\n"
            f"🕐 {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        return self._send(msg)


# ─── Singleton ────────────────────────────────────────────────
alerting_service = AlertingService()