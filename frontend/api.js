// Set your deployed backend URL here
const scanUrl = "https://lifescan-backend.onrender.com/scan"; // replace "/scan" with your endpoint path if different

document.getElementById("scan").onclick = async () => {
  const canvas = document.getElementById("canvas");
  const blob = await new Promise(res => canvas.toBlob(res, "image/jpeg"));

  const form = new FormData();
  form.append("image", blob, "scan.jpg");

  try {
    const response = await fetch(scanUrl, {
      method: "POST",
      body: form
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    document.getElementById("result").textContent =
      JSON.stringify(data, null, 2);

  } catch (error) {
    document.getElementById("result").textContent =
      "Error: " + error.message;
    console.error(error);
  }
};

