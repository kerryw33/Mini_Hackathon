const SUB_CATEGORIES = {
  need: [
    { value: "food", label: "Food" },
    { value: "housing", label: "Housing" },
    { value: "healthcare", label: "Healthcare" },
    { value: "transport", label: "Transport" },
    { value: "education", label: "Education" },
  ],
  want: [
    { value: "clothing", label: "Clothing" },
    { value: "dining out", label: "Dining Out" },
    { value: "entertainment", label: "Entertainment" },
    { value: "technology", label: "Technology" },
    { value: "travel", label: "Travel" },
  ],
  habit: [
    { value: "coffee", label: "Coffee" },
    { value: "subscriptions", label: "Subscriptions" },
    { value: "alcohol & social", label: "Alcohol & Social" },
    { value: "fitness", label: "Fitness" },
    { value: "gaming", label: "Gaming" },
  ],
};

function renderSubCategoryOptions(category) {
  const select = document.getElementById("sub_category");
  if (!select) return;

  const options = SUB_CATEGORIES[category] || [];
  select.innerHTML = "";

  options.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  });
}

function handleCategoryChange(event) {
  renderSubCategoryOptions(event.target.value);
}

window.addEventListener("DOMContentLoaded", () => {
  const category = document.getElementById("category");
  if (!category) return;

  category.addEventListener("change", handleCategoryChange);
  renderSubCategoryOptions(category.value);
});
