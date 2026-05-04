"""
RAG Service — Retrieval Augmented Generation
Menggunakan Ollama + Qwen2.5 14B (lokal) sebagai LLM
dan ChromaDB untuk semantic search dokumen kebijakan kredit.

Cara kerja:
1. Load dokumen kebijakan kredit dari file .md
2. Potong jadi chunks kecil (supaya pencarian lebih presisi)
3. Simpan ke ChromaDB sebagai vektor
4. Saat ada pertanyaan → cari chunks relevan → kirim ke Qwen → jawab
"""

import chromadb
import httpx
import re
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import Optional

# ─── Path ke dokumen kebijakan ────────────────────────────────
POLICY_DIR = Path(__file__).parent.parent.parent.parent / "data" / "policy_docs"
CHROMA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"

# ─── Ollama config ────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:14b"


class RAGService:
    """
    Service untuk RAG — mencari referensi dan menghasilkan penjelasan.
    Di-load sekali saat startup, dipakai berulang kali untuk setiap request.
    """

    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self._loaded = False

    def load(self):
        """
        Inisialisasi ChromaDB.
        Dipanggil sekali saat server startup.
        """
        if self._loaded:
            return

        print("🔍 Loading RAG service...")

        # ─── Setup ChromaDB ────────────────────────────────────
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        # Embedding function — mengubah teks menjadi vektor angka
        # all-MiniLM-L6-v2 adalah model kecil tapi akurat untuk semantic search
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Buat atau ambil collection yang sudah ada
        self.collection = self.chroma_client.get_or_create_collection(
            name="credit_policy",
            embedding_function=embedding_fn,
        )

        # Jika collection masih kosong, load dokumen
        if self.collection.count() == 0:
            print("📄 Ingesting policy documents...")
            self._ingest_documents()
        else:
            print(f"📄 Collection sudah ada: {self.collection.count()} chunks")

        self._loaded = True
        print("✅ RAG service loaded!")

    def _ingest_documents(self):
        """
        Baca semua file .md dari policy_docs, potong jadi chunks,
        simpan ke ChromaDB.
        """
        documents = []
        metadatas = []
        ids = []

        for md_file in POLICY_DIR.glob("*.md"):
            print(f"   📖 Reading: {md_file.name}")
            text = md_file.read_text(encoding="utf-8")
            chunks = self._split_by_section(text)

            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                documents.append(chunk)
                metadatas.append({"source": md_file.name, "chunk_id": i})
                ids.append(f"{md_file.stem}_{i}")

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            print(f"   ✅ {len(documents)} chunks disimpan ke ChromaDB")

    def _split_by_section(self, text: str) -> list[str]:
        """Potong dokumen Markdown berdasarkan heading."""
        sections = re.split(r'\n(?=#{1,3} )', text)
        return [s.strip() for s in sections if s.strip()]

    def retrieve(self, query: str, n_results: int = 3) -> list[str]:
        """
        Cari chunks yang paling relevan dengan query.
        ChromaDB hitung kesamaan makna antara query dan semua chunks.
        """
        if not self._loaded:
            self.load()

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count()),
        )
        return results["documents"][0] if results["documents"] else []

    def _call_ollama(self, prompt: str) -> str:
        """
        Kirim prompt ke Qwen2.5 via Ollama API.

        Ollama berjalan sebagai server lokal di port 11434.
        Kita kirim HTTP request ke sana — sama seperti memanggil API eksternal,
        bedanya ini di laptop kita sendiri. Gratis dan privat!

        timeout=120 detik karena model 14B butuh waktu untuk generate jawaban.
        """
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1024,
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"]

    def explain_decision(
        self,
        application_data: dict,
        score_result: dict,
        question: Optional[str] = None,
    ) -> str:
        """
        Generate penjelasan natural language untuk keputusan kredit.

        1. Buat query berdasarkan faktor-faktor utama dari SHAP
        2. Cari referensi relevan dari ChromaDB
        3. Kirim semua ke Qwen2.5 untuk dijawab
        """
        if not self._loaded:
            self.load()

        # Cari referensi dari ChromaDB
        top_factors = score_result.get("top_factors", [])
        factor_names = [f["factor"] for f in top_factors]
        query = f"keputusan kredit {' '.join(factor_names)} income loan"
        relevant_docs = self.retrieve(query, n_results=3)
        context = "\n\n---\n\n".join(relevant_docs)

        # Format top factors untuk prompt
        factors_text = ""
        for f in top_factors:
            impact_text = "membantu persetujuan" if f["impact"] == "positive" else "menambah risiko"
            factors_text += f"  - {f['factor']}: {impact_text}\n"

        status = "DISETUJUI ✅" if score_result["is_approved"] else "DITOLAK ❌"
        default_question = (
            "Tolong jelaskan mengapa aplikasi saya disetujui dan apa yang perlu dipertahankan."
            if score_result["is_approved"]
            else "Tolong jelaskan mengapa aplikasi saya ditolak dan bagaimana cara meningkatkan peluang persetujuan."
        )
        user_question = question or default_question

        prompt = f"""Kamu adalah analis kredit profesional dari sebuah bank di Indonesia.
Tugasmu adalah menjelaskan keputusan kredit kepada nasabah dengan bahasa yang ramah, jelas, dan mudah dipahami.

## Data Aplikasi Nasabah:
- Usia: {application_data.get('age')} tahun
- Pendapatan tahunan: Rp {application_data.get('income'):,}
- Jumlah pinjaman: Rp {application_data.get('loan_amount'):,}
- Status kepemilikan rumah: {application_data.get('home_ownership')}
- Lama bekerja: {application_data.get('emp_length')} tahun
- Tujuan pinjaman: {application_data.get('loan_intent')}
- Grade pinjaman: {application_data.get('loan_grade')}
- Pernah default sebelumnya: {application_data.get('previous_default')}

## Hasil Penilaian:
- Status: {status}
- Credit Score: {score_result['credit_score']:.1f} / 100
- Probabilitas Gagal Bayar: {score_result['probability_default']*100:.1f}%

## Faktor-Faktor Utama yang Mempengaruhi Keputusan:
{factors_text}

## Referensi Kebijakan Bank:
{context}

## Pertanyaan Nasabah:
{user_question}

## Instruksi:
- Jawab dalam Bahasa Indonesia yang ramah dan profesional
- Jelaskan faktor-faktor yang mempengaruhi keputusan dengan bahasa sederhana
- Jika ditolak, berikan saran konkret untuk meningkatkan peluang persetujuan
- Jangan sebutkan istilah teknis seperti SHAP value kepada nasabah
- Maksimal 3 paragraf, padat dan jelas
- Akhiri dengan kalimat yang memotivasi atau menawarkan bantuan lebih lanjut

Jawaban:"""

        return self._call_ollama(prompt)

    def ask_question(self, question: str) -> str:
        """Jawab pertanyaan bebas seputar kredit menggunakan RAG."""
        if not self._loaded:
            self.load()

        relevant_docs = self.retrieve(question, n_results=3)
        context = "\n\n".join(relevant_docs)

        prompt = f"""Kamu adalah asisten kredit bank yang membantu nasabah memahami produk dan kebijakan kredit.
Jawab pertanyaan berikut berdasarkan kebijakan bank kami.

## Referensi Kebijakan Bank:
{context}

## Pertanyaan Nasabah:
{question}

## Instruksi:
- Jawab dalam Bahasa Indonesia yang ramah dan mudah dipahami
- Gunakan referensi kebijakan di atas jika relevan
- Maksimal 2 paragraf
- Jika pertanyaan tidak berkaitan dengan kredit, arahkan kembali ke topik kredit

Jawaban:"""

        return self._call_ollama(prompt)


# ─── Singleton instance ───────────────────────────────────────
rag_service = RAGService()