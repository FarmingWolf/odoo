function toggleLoginMethod() {

    let a = 'toggleLoginMethod';
    console.log(a);

    const passwordLogin = document.getElementById('div_login');
    const qrCodeLogin = document.getElementById('div_wechat_qr_code');

    if (passwordLogin.style.display === 'none') {
        passwordLogin.style.display = 'block';
        qrCodeLogin.style.display = 'none';
    } else {
        passwordLogin.style.display = 'none';
        qrCodeLogin.style.display = 'block';
    }
};
