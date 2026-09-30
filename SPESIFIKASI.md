# Spesifikasi Bahasa JakselScript v0.4

> Bahasa pemrograman guyonan berbahasa gaul Jaksel.
> Ditulis dalam bahasa yang kamu pahami. Dijalankan dengan bangga.

## 1. Filosofi

- Keyword Bahasa Indonesia gaul (Jaksel), bukan Inggris.
- Sintaks eksplisit pakai kurung kurawal `{ }` (gaya C/Java) — jelas di mana blok mulai & selesai.
- Interpreted: file `.jaksel` dijalankan langsung via `jaksel gas`.
- Error message ikut gaul tapi tetap membantu.

## 2. Kata kunci

| Keyword | Arti | Setara |
|---|---|---|
| `spill(...)` | cetak ke layar | print |
| `kepo(...)` | baca input user | input |
| `bestie nama = ...` | deklarasi variabel | let/var |
| `kalo` | jika | if |
| `plot_twist` | else | else |
| `plot_twist kalo` | else-if | elif |
| `selama` | perulangan while | while |
| `gamon` | loop selamanya | while true |
| `stalk x dalam daftar` | perulangan for-each | for |
| `stalk i, x dalam daftar` | for-each dengan indeks | enumerate |
| `x dalam daftar/teks/kamus` | cek keanggotaan | in |
| `ghosting` | keluar dari loop | break |
| `skip` | lewati iterasi | continue |
| `talent nama(...)` | definisi fungsi | function |
| `talent f(a, b = 1)` | parameter default | default args |
| `balikin ...` | kembalikan nilai | return |
| `valid` / `gimmick` | benar / salah | true/false |
| `zonk` | kosong | null |
| `nggak` | bukan/tidak | not |
| `dan` / `atau` | dan / atau | and/or |
| `yolo` / `yaudah` / `akhirnya` | coba / tangkap error / selalu jalan | try/catch/finally |
| `red_flag(...)` | lempar error | throw |
| `kelas Nama { ... }` | definisi kelas | class |
| `kelas Anak warisi Ibu` | pewarisan | extends |
| `ini.atribut` | instance saat ini | this/self |
| `ortu.metode()` | panggil metode induk | super |
| `collab "..."` | import file lain / std / paket | import |
| `healing(...)` | tidur n detik | sleep |
| `cabut` | keluar program | exit |
| `//` | komentar | // |

## 3. Tipe data

- **angka**: bulat & desimal (`42`, `3.14`, `-7`)
- **teks**: `"..."` atau `'...'` (mendukung escape `\n \t \" \\`),
  plus **interpolasi**: `"Halo, {nama}! Tahun depan {umur + 1}."`
  — ekspresi apa pun boleh di dalam `{...}`; tulis `{{` / `}}` untuk
  kurung kurawal literal
- **valid/gimmick**: boolean
- **zonk**: null
- **daftar**: `[1, 2, 3]`, `"halo"` bisa diindeks juga
- **kamus**: `{ "nama": "Budi", umur: 20 }`

## 4. Operator

- Aritmetika: `+ - * / %` (tambah/kurang/kali/bagi/sisa)
- `+` juga menggabung teks: `"halo " + "rek"`
- Perbandingan: `== != < > <= >=`
- Logika: `dan`, `atau` (short-circuit), `nggak`
- Keanggotaan: `dalam` — `"a" dalam "abc"`, `2 dalam [1, 2]`,
  `"k" dalam {"k": 1}` (cek kunci kamus)
- Assignment: `=` (termasuk `daftar[0] = x`, `kamus.kunci = x`,
  `objek.atribut = x`)

Urutan prioritas (dari kuat ke lemah): `()` → unary (`-`, `nggak`) →
`* / %` → `+ -` → perbandingan → `dan` → `atau`.

## 5. Fungsi

```
talent sapa(nama) {
    balikin "Halo, " + nama + "!"
}
spill(sapa("Budi"))
```

- Parameter by value, mendukung rekursi & closure.
- Parameter default: `talent sapa(nama, sapaan = "halo")` — argumen default
  harus di belakang; boleh dioverride saat pemanggilan.
- `balikin` tanpa nilai = `balikin zonk`.

## 6. Kontrol alur

```
kalo umur < 0 {
    red_flag("Umur minus? Gimmick banget.")
} plot_twist kalo umur < 17 {
    spill("Belum valid.")
} plot_twist {
    spill("Valid!")
}

selama nyawa > 0 {
    nyawa = nyawa - 1
    kalo nyawa == 3 { ghosting }
}

stalk buah dalam ["apel", "mangga"] {
    spill(buah)
}

stalk i, buah dalam ["apel", "mangga"] {
    spill(teks(i) + ": " + buah)   // i = 0, 1, ...
}

gamon {
    spill("nyangkut...")
    ghosting
}
```

## 7. Error handling

```
yolo {
    red_flag("ada red flag!")
} yaudah e {
    spill("Ketangkep: " + e)
}
```

`yaudah` boleh tanpa variabel penangkap. Blok `akhirnya` (finally) selalu
dijalankan — sukses, error, `balikin`, `ghosting`, `skip`, maupun `cabut`:

```
yolo {
    red_flag("duar")
} yaudah e {
    spill("ketangkep: " + e)
} akhirnya {
    spill("selalu jalan, bestie.")
}
```

Error yang tidak tertangkap mencetak **jejak tumpukan** (stack trace):
nama fungsi + nomor baris tiap frame, dari yang terdalam ke terluar.

## 8. Modul

`collab "utils"` memuat `utils.jaksel` dari folder yang sama
(otomatis tambah ekstensi `.jaksel`), dieksekusi sekali saja.

Urutan pencarian `collab "x"`:
1. folder file program (`./x.jaksel`),
2. modul standar bawaan (`jaksel/std/x.jaksel`),
3. paket user di `~/.jaksel/paket/` (`x` = `namapaket/file`).

### Modul standar (`jaksel/std/`)

| Modul | Isi |
|---|---|
| `std/teks` | `judul()`, `slug()`, `balik()`, `hitung_kata()`, `kamel()`, `ular()` |
| `std/angka` | `faktorial()`, `fpb()`, `kpk()`, `prima()`, `fib()`, `median()`, `bulat_bawah()`, `bulat_atas()` |
| `std/waktu` | `tanggal_cantik()`, `tambah_hari()`, `selisih_hari()`, `nama_hari()`, `nama_bulan()` |
| `std/http` | `http_ambil_json()`, `http_kirim_json()` (pembungkus gampang) |

Pakai: `collab "std/teks"` lalu `spill(slug("Halo Dunia"))`.

### Package manager mini

```bash
jaksel pasang <url-git / folder>   # install paket .jaksel ke ~/.jaksel/paket/
jaksel paket                       # daftar paket terpasang
jaksel lepas <nama>                # hapus paket
```

Lalu pakai dari kode: `collab "namapaket/file"`.

## 9. Kelas & OOP

```jaksel
kelas Hewan {
    talent lahir(nama) {        // constructor
        ini.nama = nama
    }
    talent suara() {
        balikin "..."
    }
    talent tampil() {           // representasi teks objek (dipakai spill/teks)
        balikin ini.nama + " bersuara " + ini.suara()
    }
}

kelas Kucing warisi Hewan {
    talent lahir(nama, warna = "oren") {
        ortu.lahir(nama)        // panggil constructor induk
        ini.warna = warna
    }
    talent suara() {            // override
        balikin "meong"
    }
}

bestie tom = Kucing("Tom")      // kelas dipanggil = constructor
tom.sapa()                      // panggil method
spill(tom.warna)                // baca atribut
spill(tipe(tom))                // "Kucing"
bestie f = tom.suara            // method sebagai nilai (bound method)
spill(f())                      // "meong"
```

- `lahir` = constructor; kalau tidak didefinisikan, constructor induk dipakai.
- `ini` = instance saat ini; `ortu.metode()` = panggil metode induk
  (method lookup dimulai dari kelas induk, bukan dari kelas pemilik `ini`).
- Pewarisan melingkar (langsung/tak langsung) ditolak dengan error jelas.
- `tampil()` opsional: kalau ada, `spill(objek)` / `teks(objek)` memakainya.

## 10. Fungsi bawaan

| Fungsi | Keterangan |
|---|---|
| `spill(...)` | cetak 1+ argumen dipisah spasi |
| `kepo(prompt)` | tampilkan prompt, baca 1 baris |
| `healing(detik)` | jeda n detik (boleh desimal) |
| `panjang(x)` | panjang teks/daftar/kamus |
| `angka(x)` | konversi ke angka |
| `teks(x)` | konversi ke teks |
| `rentang(n)` / `rentang(a, b)` / `rentang(a, b, step)` | daftar angka 0..n-1 (kayak `range`) |
| `acak()` / `acak(b)` / `acak(a, b)` | float 0–1 / int acak 0..b-1 / int acak a..b-1 |
| `waktu()` | detik epoch (float) |
| `tanggal()` / `tanggal(format)` | tanggal & jam sekarang; format ala `strftime`,
  mis. `tanggal("%d-%m-%Y")`. Default: `"%d/%m/%Y %H:%M:%S"` |
| `red_flag(pesan)` | lempar error (statement) |
| `tipe(x)` | nama tipe: `angka`/`teks`/`daftar`/`kamus`/`fungsi`/`kelas`/`zonk`/nama kelas |
| `klaim(kondisi, pesan?)` | assert: error kalau kondisi gimmick |
| `args()` | daftar argumen baris perintah setelah nama file |
| `env(nama, default?)` | baca environment variable |

### Scripting: JSON, HTTP, regex, CSV

| Fungsi | Keterangan |
|---|---|
| `json_tulis(x, cantik?)` | nilai → teks JSON (`cantik=valid` = pretty) |
| `json_urai(teks)` | teks JSON → nilai JakselScript |
| `http_get(url)` | GET → teks body |
| `http_get_json(url)` | GET → nilai (parse JSON) |
| `http_post(url, data)` | POST form-urlencoded → teks body |
| `cocok(teks, pola)` | `valid` kalau regex cocok di mana saja |
| `cocok_penuh(teks, pola)` | `valid` kalau regex cocok seluruh teks |
| `cari(teks, pola)` | cocok pertama (teks kosong kalau nggak ada) |
| `cari_semua(teks, pola)` | daftar semua cocok |
| `ganti_regex(teks, pola, ganti)` | ganti semua cocok pola |
| `pisah_regex(teks, pola)` | pisah teks pakai pola regex |
| `csv_baca(path)` | baca CSV → daftar baris (daftar kolom) |
| `csv_tulis(path, data)` | tulis daftar baris ke CSV |

### File & folder

Path relatif selalu dihitung dari **folder file program**, bukan dari
current working directory. Path absolut dibiarkan apa adanya.

| Fungsi | Keterangan |
|---|---|
| `baca_file(path)` | baca seluruh isi file jadi teks |
| `tulis_file(path, teks)` | tulis (timpa) file |
| `tambah_file(path, teks)` | tambah ke akhir file |
| `ada_file(path)` | `valid`/`gimmick`: file/folder ada? |
| `daftar_file(folder?)` | daftar nama isi folder (terurut) |
| `buat_folder(path)` | bikin folder (+ induknya) |
| `hapus_file(path)` | hapus file |

### Agregat

| Fungsi | Keterangan |
|---|---|
| `total(daftar)` | jumlah semua elemen |
| `terbesar(daftar)` / `terkecil(daftar)` | nilai maksimum / minimum |
| `rerata(daftar)` | rata-rata |
| `urut_dengan(daftar, kunci?)` | urut pakai fungsi kunci (default: nilai) |
| `pasangkan(a, b)` | zip: `[[a0, b0], [a1, b1], ...]` |

### Shell

| Fungsi | Keterangan |
|---|---|
| `jalankan(perintah)` | jalankan perintah shell → kamus `{kode, keluar, galat}` |

> ⚠️ `jalankan()` memakai shell sistem — jangan teruskan input user
> mentah-mentah ke sana (risiko command injection). Untuk perintah
> tetap/terpercaya saja.

### Fungsi tingkat tinggi

Menerima `talent` sebagai argumen — bisa di-chaining:

```
talent genap(x) { balikin x % 2 == 0 }
talent kuadrat(x) { balikin x * x }

spill(saring([1, 2, 3, 4], genap))       // [2, 4]
spill(petakan([1, 2, 3], kuadrat))       // [1, 4, 9]
spill(kumpulkan([1, 2, 3], tambah, 0))   // 6  (reduce)
```

| Fungsi | Keterangan |
|---|---|
| `petakan(daftar, f)` | map: tiap elemen dilewatkan ke `f(x)` |
| `saring(daftar, f)` | filter: cuma elemen yang bikin `f(x)` truthy |
| `kumpulkan(daftar, f, awal)` | reduce: `acc = f(acc, x)` dari nilai `awal` |

### File I/O

| Fungsi | Keterangan |
|---|---|
| `baca_file(path)` | baca seluruh isi file jadi teks (error kalau nggak ada) |
| `tulis_file(path, teks)` | tulis file (timpa kalau sudah ada) |
| `tambah_file(path, teks)` | tambah teks ke akhir file |

Path relatif dibaca dari direktori kerja saat program dijalankan.

## 11. Method

Method nempel ke nilai pakai titik: `objek.nama(args)`.

### Method daftar

| Method | Keterangan |
|---|---|
| `tambah(x)` | tambah elemen ke akhir (kembalikan daftarnya) |
| `buang(i?)` | buang & kembalikan elemen index `i` (default: terakhir) |
| `sisipkan(i, x)` | selipkan `x` di posisi `i` |
| `urut()` | urutkan di tempat |
| `balik()` | balik urutan di tempat |
| `gabung(pemisah)` | gabung semua elemen jadi teks |
| `salin()` | salinan daftar (biar aslinya nggak kesentuh) |

### Method teks

| Method | Keterangan |
|---|---|
| `besar()` | jadi HURUF KAPITAL |
| `kecil()` | jadi huruf kecil |
| `potong()` | buang spasi di ujung-ujung |
| `ganti(lama, baru)` | ganti semua kemunculan |
| `pisah(pemisah?)` | pecah jadi daftar (default: pecah per whitespace) |
| `mulai_dengan(awalan)` | valid/gimmick |
| `berakhir_dengan(akhiran)` | valid/gimmick |

### Method kamus

| Method | Keterangan |
|---|---|
| `kunci()` | daftar semua kunci |
| `nilai()` | daftar semua nilai |
| `ambil(kunci, default?)` | ambil aman — `zonk`/default kalau kunci nggak ada |
| `hapus(kunci)` | hapus & kembalikan nilainya |

Method yang dipanggil di tipe yang salah ngasih error jelas, mis.
`(5).tambah(1)` → `angka nggak punya method 'tambah', bestie.`

## 12. CLI

```
jaksel gas program.jaksel              # jalankan file
jaksel gas program.jaksel a1 a2        # + argumen (dibaca via args())
jaksel cek program.jaksel              # cek sintaks tanpa menjalankan
jaksel alihbahasakan program.jaksel    # terjemahkan ke Python (.py)
jaksel rapi program.jaksel             # auto-format kode di tempat
jaksel rapi --cek program.jaksel       # cek aja: exit 1 kalau belum rapi
jaksel rapi --stdout program.jaksel    # cetak hasil format ke stdout
jaksel urai program.jaksel             # intip token & AST
jaksel urai --token program.jaksel     # token saja
jaksel urai --ast program.jaksel       # AST saja
jaksel lsp                             # language server (stdio, buat editor)
jaksel debug program.jaksel            # debugger interaktif
jaksel pasang <url-git/folder>         # install paket .jaksel
jaksel paket                           # daftar paket terpasang
jaksel lepas <nama>                    # hapus paket
jaksel                                 # REPL interaktif
jaksel versi                           # tampilkan versi
```

### Debugger (`debug`)

Debugger interaktif berbasis CLI:

```
debug>                     # Enter = eksekusi 1 baris (step)
debug> b 12                # pasang breakpoint di baris 12
debug> lanjut               # jalan sampai breakpoint berikutnya / selesai
debug> p umur + 1          # cetak nilai ekspresi di konteks saat ini
debug> tumpuk              # tampilkan jejak tumpukan
debug> hapus 12            # hapus breakpoint
debug> keluar              # hentikan sesi debug
```

Breakpoint dievaluasi sebelum baris dieksekusi; `lanjut` jalan sampai
breakpoint berikutnya.

### REPL

REPL interaktif dengan **riwayat persisten** (`~/.jaksel/repl_history`,
navigasi pakai panah atas/bawah) dan **mode multiline**: blok yang
kurung kurawalnya belum seimbang dilanjutkan ke baris berikutnya.

### Formatter (`rapi`)

- Indent 4 spasi, spasi konsisten di sekitar operator & koma, gaya kurung
  kurawal K&R (`} plot_twist {`).
- **Idempoten**: diformat dua kali hasilnya sama.
- Komentar `//` dipertahankan (leading & trailing).
- Contoh di folder `contoh/` semuanya lolos `jaksel rapi --cek`.

### Inspector (`urai`)

Menampilkan token (baris:kolom, jenis, nilai) dan struktur AST —
berguna buat debugging dan belajar cara kerja bahasa.

### Language server (`lsp`)

Server LSP via stdio (tanpa dependensi), dipakai extension VS Code:

- **Diagnostics**: error sintaks real-time (setara `jaksel cek`).
- **Hover**: dokumentasi keyword, fungsi bawaan, dan method.
- **Completion**: keyword, fungsi bawaan, variabel/`talent` yang
  dideklarasikan, plus method setelah titik (mis. ketik `buah.`).

### Transpiler (`alihbahasakan`)

Menerjemahkan `.jaksel` menjadi Python murni yang setara secara semantik:

- Semua keyword diterjemahkan (`spill` → print berformat Jaksel,
  `gamon` → `while True`, `yolo`/`yaudah` → `try`/`except`, dst).
- Operasi aritmetika/perbandingan/index memakai helper `_cek` yang
  melempar `_RedFlag` dengan pesan gaya Jaksel — jadi `yolo` tetap
  bisa menangkap type error & pembagian nol seperti di interpreter.
- `collab` di-inline (isi file yang diimpor disisipkan, anti sirkular).
- Hasilnya bisa dibaca, dimodifikasi, dan dijalankan tanpa JakselScript.

## 13. Error message

Setiap error menampilkan pesan gaya Jaksel **plus snippet kode sumber**
dan tanda `^` di posisi error, contoh:

```
Gimmick nih sintaksnya (baris 1, kolom 18): string nggak ditutup, bestie. Mana quote pasangannya?
  1 | spill("lupa tutup
                       ^
```

### Saran typo

Kalau nama variabel, fungsi bawaan, atau method salah ketik tapi mirip
dengan yang dikenal, error-nya ngasih saran:

```jaksel
Red flag baris 1: variabel 'spilll' belum dikenalin, bestie. ... Maksudnya 'spill'?
Red flag baris 2: daftar nggak punya method 'tambha', bestie. Maksudnya 'tambah'?
Gimmick nih sintaksnya (baris 1, kolom 1): 'kallo' nggak dikenal di sini, bestie. Maksudnya 'kalo'?
```

Saran keyword aktif di awal statement (selain assignment & pemanggilan),
jadi typo keyword umum langsung ketahuan di parser.

## 14. Contoh program

Lihat folder `contoh/`.
