const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const quickButtons = document.querySelectorAll("[data-question]");

function addMessage(text, role) {
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.append(paragraph);

  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

function setAssistantResponse(message, text, products = []) {
  message.className = "message assistant";
  message.removeAttribute("aria-label");
  message.innerHTML = "";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  message.append(paragraph);

  if (products.length) {
    const productList = document.createElement("div");
    productList.className = "product-results";

    products.forEach((product) => {
      const card = document.createElement("a");
      card.className = "product-card";
      card.href = product.url;
      card.target = "_blank";
      card.rel = "noopener noreferrer";

      const image = document.createElement("img");
      image.src = product.images[0];
      image.alt = product.name || "Mahsulot rasmi";
      image.loading = "lazy";
      card.append(image);

      const body = document.createElement("div");
      body.className = "product-card-body";

      const category = document.createElement("span");
      category.className = "product-category";
      category.textContent = product.category || "Mahsulot";

      const title = document.createElement("strong");
      title.textContent = product.name || "Mahsulot";

      const price = document.createElement("span");
      price.className = "product-price";
      price.textContent = product.price || "Narx operator orqali tasdiqlanadi";

      body.append(category, title, price);
      card.append(body);
      productList.append(card);
    });

    message.append(productList);
  }
}

function setLoading(isLoading) {
  input.disabled = isLoading;
  form.querySelector("button").disabled = isLoading;
  quickButtons.forEach((button) => {
    button.disabled = isLoading;
  });
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message) return;

  addMessage(message, "user");
  input.value = "";
  setLoading(true);
  const loading = addTypingIndicator();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    setAssistantResponse(loading, data.answer || "Javob topilmadi.", data.products || []);
  } catch {
    setAssistantResponse(loading, "Aloqa xatosi. Iltimos, qayta urinib ko'ring.");
  } finally {
    setLoading(false);
    input.focus();
    messages.scrollTop = messages.scrollHeight;
  }
}

function addTypingIndicator() {
  const message = document.createElement("article");
  message.className = "message assistant typing-message";
  message.setAttribute("aria-label", "Javob yozilmoqda");

  const indicator = document.createElement("div");
  indicator.className = "typing";
  indicator.innerHTML = "<span></span><span></span><span></span>";
  message.append(indicator);

  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

quickButtons.forEach((button) => {
  button.addEventListener("click", () => {
    sendMessage(button.dataset.question || "");
  });
});
