from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

from werkzeug.utils import secure_filename

import os
import sqlite3
from functools import wraps


# ============================================================
# KONFIGURASI APLIKASI
# ============================================================

app = Flask(__name__)

# Ganti dengan secret key sendiri jika aplikasi sudah online
app.secret_key = "perangkat-ajar-guru-secret-key-2026"

# Ukuran maksimum upload = 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


# ============================================================
# LOKASI DATABASE DAN UPLOAD
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "database.db"
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Membuat folder upload jika belum ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# EXTENSION FILE YANG DIIZINKAN
# ============================================================

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "jpg",
    "jpeg",
    "png"
}


def allowed_file(filename):
    """
    Mengecek apakah ekstensi file diperbolehkan.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    """
    Membuka koneksi ke database SQLite.
    """

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(view):
    """
    Decorator untuk halaman yang hanya boleh
    diakses oleh pengguna yang sudah login.
    """

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Silakan login terlebih dahulu.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped_view


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(*allowed_roles):
    """
    Membatasi halaman berdasarkan role pengguna.
    """

    def decorator(view):

        @wraps(view)
        def wrapped_view(*args, **kwargs):

            if "user_id" not in session:

                flash(
                    "Silakan login terlebih dahulu.",
                    "warning"
                )

                return redirect(
                    url_for("login")
                )

            current_role = session.get("role")

            if current_role not in allowed_roles:

                flash(
                    "Anda tidak memiliki akses ke halaman tersebut.",
                    "danger"
                )

                return redirect(
                    url_for("dashboard")
                )

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


# ============================================================
# HALAMAN UTAMA
# ============================================================

@app.route("/")
def index():

    if "user_id" in session:

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Jika sudah login
    if "user_id" in session:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        if not username or not password:

            flash(
                "Username dan password wajib diisi.",
                "warning"
            )

            return render_template(
                "login.html"
            )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:

            # Bersihkan session lama
            session.clear()

            # Simpan session pengguna
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash(
                "Login berhasil. Selamat datang!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Username atau password salah.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Anda telah keluar dari sistem.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# DASHBOARD UTAMA BERDASARKAN ROLE
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    role = session.get("role")

    if role == "guru":

        return redirect(
            url_for("guru_dashboard")
        )

    elif role == "kepala_sekolah":

        return redirect(
            url_for("kepala_sekolah_dashboard")
        )

    elif role == "pengawas":

        return redirect(
            url_for("pengawas_dashboard")
        )

    elif role == "dinas":

        return redirect(
            url_for("dinas_dashboard")
        )

    flash(
        "Role pengguna tidak dikenali.",
        "danger"
    )

    return redirect(
        url_for("logout")
    )


# ============================================================
# DASHBOARD GURU
# ============================================================

@app.route("/guru/dashboard")
@login_required
@role_required("guru")
def guru_dashboard():

    user_id = session["user_id"]

    conn = get_db()

    # --------------------------------------------------------
    # TOTAL PERANGKAT GURU
    # --------------------------------------------------------

    total_perangkat = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM perangkat_ajar
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()["total"]


    # --------------------------------------------------------
    # STATUS MENUNGGU
    # --------------------------------------------------------

    menunggu = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM perangkat_ajar
        WHERE user_id = ?
        AND UPPER(status) = 'MENUNGGU'
        """,
        (user_id,)
    ).fetchone()["total"]


    # --------------------------------------------------------
    # STATUS DIPROSES
    # --------------------------------------------------------

    diproses = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM perangkat_ajar
        WHERE user_id = ?
        AND UPPER(status) = 'DIPROSES'
        """,
        (user_id,)
    ).fetchone()["total"]


    # --------------------------------------------------------
    # STATUS SELESAI / DISETUJUI
    # --------------------------------------------------------

    selesai = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM perangkat_ajar
        WHERE user_id = ?
        AND UPPER(status) IN (
            'SELESAI',
            'DISETUJUI',
            'DISETUJUI KEPALA SEKOLAH'
        )
        """,
        (user_id,)
    ).fetchone()["total"]


    # --------------------------------------------------------
    # STATUS DITOLAK
    # --------------------------------------------------------

    ditolak = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM perangkat_ajar
        WHERE user_id = ?
        AND UPPER(status) = 'DITOLAK'
        """,
        (user_id,)
    ).fetchone()["total"]


    # --------------------------------------------------------
    # 5 PERANGKAT TERBARU
    # --------------------------------------------------------

    perangkat_terbaru = conn.execute(
        """
        SELECT *
        FROM perangkat_ajar
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (user_id,)
    ).fetchall()


    conn.close()


    return render_template(
        "guru/dashboard.html",

        total_perangkat=total_perangkat,

        menunggu=menunggu,

        diproses=diproses,

        selesai=selesai,

        ditolak=ditolak,

        perangkat_terbaru=perangkat_terbaru
    )


# ============================================================
# DAFTAR PERANGKAT GURU
# ============================================================

@app.route("/guru/perangkat")
@login_required
@role_required("guru")
def guru_perangkat():

    user_id = session["user_id"]

    conn = get_db()

    perangkat = conn.execute(
        """
        SELECT *
        FROM perangkat_ajar
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "guru/perangkat.html",
        perangkat=perangkat
    )


# ============================================================
# TAMBAH PERANGKAT
# ============================================================

@app.route(
    "/guru/perangkat/tambah",
    methods=["GET", "POST"]
)
@login_required
@role_required("guru")
def tambah_perangkat():

    if request.method == "POST":

        # ----------------------------------------------------
        # AMBIL DATA FORM
        # ----------------------------------------------------

        judul = request.form.get(
            "judul",
            ""
        ).strip()

        if not judul:

            flash(
                "Judul perangkat ajar wajib diisi.",
                "warning"
            )

            return render_template(
                "guru/tambah_perangkat.html"
            )


        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        file = request.files.get("file")


        if not file or file.filename == "":

            flash(
                "Silakan pilih file perangkat ajar.",
                "warning"
            )

            return render_template(
                "guru/tambah_perangkat.html"
            )


        if not allowed_file(file.filename):

            flash(
                "Format file tidak diperbolehkan.",
                "danger"
            )

            return render_template(
                "guru/tambah_perangkat.html"
            )


        # ----------------------------------------------------
        # NAMA FILE AMAN
        # ----------------------------------------------------

        filename = secure_filename(
            file.filename
        )


        # Jika nama file sudah ada,
        # tambahkan nomor unik
        original_name = filename

        counter = 1

        while os.path.exists(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        ):

            name, ext = os.path.splitext(
                original_name
            )

            filename = (
                f"{name}_{counter}{ext}"
            )

            counter += 1


        # ----------------------------------------------------
        # SIMPAN FILE
        # ----------------------------------------------------

        file.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )


        # ----------------------------------------------------
        # SIMPAN KE DATABASE
        # ----------------------------------------------------

        user_id = session["user_id"]

        conn = get_db()

        conn.execute(
            """
            INSERT INTO perangkat_ajar
            (
                user_id,
                judul,
                filename,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                judul,
                filename,
                "MENUNGGU"
            )
        )

        conn.commit()

        conn.close()


        flash(
            "Perangkat ajar berhasil ditambahkan dan menunggu verifikasi.",
            "success"
        )

        return redirect(
            url_for("guru_perangkat")
        )


    return render_template(
        "guru/tambah_perangkat.html"
    )


# ============================================================
# DOWNLOAD PERANGKAT
# ============================================================

@app.route(
    "/guru/perangkat/download/<filename>"
)
@login_required
def download_perangkat(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )


# ============================================================
# HAPUS PERANGKAT
# ============================================================

@app.route(
    "/guru/perangkat/hapus/<int:perangkat_id>",
    methods=["POST"]
)
@login_required
@role_required("guru")
def hapus_perangkat(perangkat_id):

    user_id = session["user_id"]

    conn = get_db()

    perangkat = conn.execute(
        """
        SELECT *
        FROM perangkat_ajar
        WHERE id = ?
        AND user_id = ?
        """,
        (
            perangkat_id,
            user_id
        )
    ).fetchone()


    if not perangkat:

        conn.close()

        flash(
            "Perangkat tidak ditemukan.",
            "danger"
        )

        return redirect(
            url_for("guru_perangkat")
        )


    # --------------------------------------------------------
    # Hapus file fisik
    # --------------------------------------------------------

    filename = perangkat["filename"]

    if filename:

        file_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        if os.path.exists(file_path):

            os.remove(file_path)


    # --------------------------------------------------------
    # Hapus database
    # --------------------------------------------------------

    conn.execute(
        """
        DELETE FROM perangkat_ajar
        WHERE id = ?
        AND user_id = ?
        """,
        (
            perangkat_id,
            user_id
        )
    )

    conn.commit()

    conn.close()


    flash(
        "Perangkat ajar berhasil dihapus.",
        "success"
    )

    return redirect(
        url_for("guru_perangkat")
    )


# ============================================================
# DASHBOARD KEPALA SEKOLAH
# ============================================================

@app.route("/kepala-sekolah/dashboard")
@login_required
@role_required("kepala_sekolah")
def kepala_sekolah_dashboard():

    return render_template(
        "kepala_sekolah/dashboard.html"
    )


# ============================================================
# DASHBOARD PENGAWAS
# ============================================================

@app.route("/pengawas/dashboard")
@login_required
@role_required("pengawas")
def pengawas_dashboard():

    return render_template(
        "pengawas/dashboard.html"
    )


# ============================================================
# DASHBOARD DINAS
# ============================================================

@app.route("/dinas/dashboard")
@login_required
@role_required("dinas")
def dinas_dashboard():

    return render_template(
        "dinas/dashboard.html"
    )


# ============================================================
# ERROR FILE TERLALU BESAR
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "Ukuran file terlalu besar. Maksimal 20 MB.",
        "danger"
    )

    return redirect(
        url_for("tambah_perangkat")
    )


# ============================================================
# ERROR UMUM
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return """
    <h2>Halaman tidak ditemukan</h2>
    <p>Halaman yang Anda cari tidak tersedia.</p>
    <a href="/">Kembali ke halaman utama</a>
    """, 404


# ============================================================
# MENJALANKAN APLIKASI
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("PERANGKAT AJAR GURU")
    print("Sistem Administrasi Pendidikan Digital")
    print("=" * 60)

    print(f"Database : {DATABASE}")
    print(f"Upload   : {UPLOAD_FOLDER}")

    print()
    print("Aplikasi berjalan pada:")
    print("http://127.0.0.1:5000")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )