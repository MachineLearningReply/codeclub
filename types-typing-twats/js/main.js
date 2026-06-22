function isPremium(users) {
  return users > "100";
}

// weak typing can induce real production bugs
console.log(isPremium("42"));   // true  ❌
console.log(isPremium("200"));  // true