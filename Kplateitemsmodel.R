# Load required libraries
library(jsonlite)
library(dplyr)
library(tidyr)
library(lubridate)
library(ggplot2)

# Read the JSON file (adjust the path if needed)
orders_data <- fromJSON("random.json")$orders

# Convert orders_data to a tibble and unnest line_items
# Using names_sep prefixes nested columns with "line_items_"
orders_df <- as_tibble(orders_data) %>%
  unnest(line_items, names_sep = "_")

# Define the items of interest, now including Tofu Plate and K-Plate
items_of_interest <- c("Spicy Chicken Plate", "Spicy Pork Plate", "Short Plate", 
                       "Soy Chicken Plate", "Beef Dumplings", "Kimchi Dumplings", 
                       "Fries", "Wings", "Tofu Plate", "K-Plate", "Mixed Veggie Plate")

# Filter for the items of interest
# Note: The item name is now in the "line_items_name" column after unnesting
sales_items <- orders_df %>%
  filter(line_items_name %in% items_of_interest) %>%
  mutate(created_at = as.Date(created_at))

# Convert quantity to numeric (the column is now "line_items_quantity")
sales_items <- sales_items %>%
  mutate(quantity = as.numeric(line_items_quantity))

# Aggregate sales by day for each item
sales_by_day <- sales_items %>%
  group_by(created_at, line_items_name) %>%
  summarise(sales_count = sum(quantity, na.rm = TRUE), .groups = "drop")

# Create a numeric time variable (days since the first date)
sales_by_day <- sales_by_day %>%
  mutate(time_numeric = as.numeric(created_at - min(created_at)))

# Fit a linear regression model for each item: sales_count ~ time_numeric
models <- sales_by_day %>%
  group_by(line_items_name) %>%
  do(model = lm(sales_count ~ time_numeric, data = .))

# Print a summary for each model
models %>% 
  rowwise() %>% 
  mutate(summary = list(summary(model))) %>% 
  select(line_items_name, summary) %>% 
  print(n = Inf)

# Plot the data and regression lines for each item using faceting
ggplot(sales_by_day, aes(x = created_at, y = sales_count)) +
  geom_point() +
  geom_smooth(method = "lm", se = FALSE) +
  facet_wrap(~ line_items_name, scales = "free_y") +
  labs(title = "Sales Over Time for Selected Items",
       x = "Date", y = "Sales Count") +
  theme_minimal()
