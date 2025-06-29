wget https://github.com/proftpd/proftpd/archive/refs/tags/v1.3.9.tar.gz
tar -xzf v1.3.9.tar.gz
cd proftpd-1.3.9
./configure \
    --prefix=/usr/local/proftpd \
    --sysconfdir=/etc/proftpd \
    --localstatedir=/var/run/proftpd \
    --mandir=/usr/share/man \
    --enable-autoshadow \
    --enable-openssl \
    --enable-auth-pam \
    --with-lastlog \
    --with-modules=mod_ratio:mod_tls # 這些是常見的模組，您可以根據需求增減
make
sudo make install