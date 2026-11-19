# Staging stand-in for the CIC web server's SFTP account (deploy/staging/README.md). Not used in production.
# One key-only, chrooted, SFTP-only user `crtdh` (uid 1001). Its writable folder /www (named volume site_www)
# plays the role of the hosting account's home: public_html lives in it, with the agent's crtdh-releases/ beside it.
# The `site` container serves the same volume read-only. The host key and the agent's public key come from
# deploy/staging/secrets/sftp (made by setup.sh), so the agent can pin the host key and it survives rebuilds.
FROM debian:bookworm-slim

# usermod -p '*': no password, but not "locked" ('!'), which sshd refuses even for key logins with UsePAM no.

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server \
    && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_* \
    && groupadd --gid 1001 crtdh \
    && useradd --uid 1001 --gid 1001 --home-dir /home/crtdh --no-create-home --shell /usr/sbin/nologin crtdh \
    && usermod -p '*' crtdh \
    && install -d -m 0755 -o root -g root /home/crtdh /run/sshd \
    && install -d -m 0755 -o crtdh -g crtdh /home/crtdh/www

COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /usr/local/bin/sftp-entrypoint
RUN chmod 0644 /etc/ssh/sshd_config && chmod 0755 /usr/local/bin/sftp-entrypoint

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/sftp-entrypoint"]
