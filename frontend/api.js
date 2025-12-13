document.getElementById("scan").onclick = async () => {
  const canvas = document.getElementById("canvas");
  const blob = await new Promise(res => canvas.toBlob(res, "image/jpeg"));

  const form = new FormData();
  form.append("image", blob, "scan.jpg");

  const response = await fetch(scanUrl, {
    method: "POST",
    body: form
  });

  const data = await response.json();
  document.getElementById("result").textContent =
    JSON.stringify(data, null, 2);
};
