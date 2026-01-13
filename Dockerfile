FROM php:8.1-apache
# Mengaktifkan ekstensi MySQL agar PHP bisa konek ke database Railway
RUN docker-php-ext-install mysqli
# Menyalin semua file dari folder lokal ke dalam server virtual
COPY . /var/www/html/
EXPOSE 80
