document.addEventListener("DOMContentLoaded", function () {
    async function connectAndSign() {
        const ncalayerClient = new NCALayerClient();
        document.getElementById("status").innerText = "Подключение к NCALayer...";

        try {
            await ncalayerClient.connect();
        } catch (error) {
            alert(`Не удалось подключиться к NCALayer: ${error.toString()}`);
            return;
        }

        document.getElementById("status").innerText = "Подключено! Выполняется подписание...";
        const groupid = document.getElementById("groupid").value;
        const documentBase64 = btoa(groupid);

        let signature;
        try {
            signature = await ncalayerClient.basicsSignCMS(
                NCALayerClient.basicsStorageAll,
                documentBase64,
                NCALayerClient.basicsCMSParamsAttached,
                NCALayerClient.basicsSignerSignAny
            );
        } catch (error) {
            alert("Ошибка подписи: " + error.toString());
            return;
        }
        if (signature.includes("-----BEGIN CMS-----")) {
            signature = signature
                .replace("-----BEGIN CMS-----", "")
                .replace("-----END CMS-----", "")
                .replace(/\r?\n|\r/g, "")
                .trim();
        }


        document.getElementById("status").innerText = "Подпись получена, отправка на сервер...";
        const bodyData = {
            signedData: signature,
            originalData: documentBase64,
            groupid: groupid
        };

        // Отправка на сервер
        const response = await fetch("/signature/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(bodyData)
        });

        const result = await response.json();

        document.getElementById("status").innerText = result.success
            ? "Подпись верна!"
            : "Ошибка проверки подписи: " + result.message;

        if (result.success && result.redirectUrl) {
            window.location.href = result.redirectUrl;
        }
    }

    // Назначаем обработчик кнопке подписания
    const signButton = document.getElementById("signButton");
    if (signButton) {
        signButton.addEventListener("click", () => {
            connectAndSign();
        });
    }
});