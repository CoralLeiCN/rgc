# Intention

Build a tool for classifying product features and analyzing how those features
relate to product pricing within a category.

The tool will support many product categories. Chocolate is an example.

## 1. Category research and a pricing model

For a chosen product category and market, collect enough product data to fit a
regression model. Chocolate sold in the United Kingdom is one example study.

Find as many types and varieties of products in the selected category as possible,
and collect:

- Prices.
- Basic product information, including complete ingredient lists, brands, and
  other relevant source statements.
- Product features.
- All identifiable points emphasized on packaging and in promotional material.

Preserve each product's original information and product images. Each product
may have its own folder, with a JSON file covering as much relevant product
information as possible. Collect many products first, then derive a complete
schema from the collected information.

The product-information collection part of category research must be available as
an agent plugin that can connect to multiple agent harnesses and be integrated
with other plugins. Follow the Agent Plugins specification at
https://agent-plugins.org/specification.

Use the collected data to estimate the contribution of individual product
features to the final price. Examples include fair trade, brand, and nuts.

## 2. Price testing for a newly designed product

A brand, as a user of the application, can use the model to test the price of a
newly designed product.

## 3. Category value for money and brand premium

Develop a category-based value-for-money score to assess how much brand premium
a product carries.

Implementation of this feature is deferred. Research suitable scientific methods
first.

## Repository language

All repository content must be in English, even when prompts are written in
Chinese.
