Onegov Quill
============

Quill rich text editor integration for OneGov.

Updating Quill.js
-----------------

We use a custom version of Quill.js which adds missing SVGs. Update it with::

    # Cloning the fork
    git clone git@github.com:seantis/quill.git
    cd quill
    git checkout 1.3.7

    # Installing requirements, see https://stackoverflow.com/a/53256307
    sudo apt install ruby-dev ruby-bundler
    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
    sudo bundle update --bundler
    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0
    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0

    # Building
    npm install
    bundle install
    npm run build
    cp dist/quill.js ../assets/js
    cp dist/quill.snow.css ../assets/css
