---
layout: default
title: "How to Style With Web Components"
date: 2023-12-07
categories: webdevelopment frontend shadowdom
---

The Shadow DOM is a powerful part of modern web development, providing encapsulation for CSS and JavaScript. But with great power comes great responsibility—and sometimes, great complexity. I recently encountered a styling challenge while working with the Shadow DOM, and I wanted to share my experience and solutions.

## What is the Shadow DOM?

Before diving into the problem, let's quickly revisit what the Shadow DOM is. It's a separate DOM tree attached to elements, invisible to the main document's DOM tree. It allows for component-style encapsulation, meaning whatever happens in the Shadow DOM, stays in the Shadow DOM. This encapsulation is fantastic for widget-like components, but it can also lead to styling challenges.

{% capture basic_example %}
<custom-element class="my-style-that-does-not-work">
  #shadow-root
    <div>Styling me is not so straightforward!</div>
</custom-element>
{% endcapture %}
{% include code_card.html content=basic_example %}

## The Challenge

The task was easy enough: style a wired-card element with social icons and copyright text, making sure they align perfectly within the footer. However, the wired-card creates its own shadow root, and none of the styles defined in the main document's CSS were being applied.

{% capture wired_card_example %}
<footer>
  <wired-card elevation="2" class="footer-card">
    <!-- Expected to style these... but no luck! -->
    <div id="foo">Foo</div>
    <div id="bar">Bar</div>
  </wired-card>
</footer>
{% endcapture %}
{% include code_card.html content=wired_card_example %}

#### Example:

<wired-card elevation="2" class="shadowdom example">
  <div id="foo">Foo</div>
  <div id="bar">Bar</div>
</wired-card>

## The Revelation

After some investigation and many console.log's later, the realization dawned on me: the styles weren't penetrating the Shadow DOM. The Shadow DOM's encapsulation was doing its job a little too well.

## The Solution

The solution came in the form of a wrapper. By placing a div inside the wired-card, I could apply styles to the div, which would not be affected by the Shadow DOM encapsulation.

{% capture wired_card_solution %}
<footer>
  <wired-card elevation="2">
    <!-- This div acts as a style wrapper -->
    <div class="footer-card">
      <div>Foo</div>
      <div>Bar</div>
    </div>
  </wired-card>
</footer>
{% endcapture %}
{% include code_card.html content=wired_card_solution %}

#### Example:
<wired-card elevation="2" class="shadowdom">
  <div class="example">
    <div id="foo">Foo</div>
    <div id="bar">Bar</div>
  </div>
</wired-card>

And the CSS:

{% capture wired_card_css %}
/* The CSS that might be used */
.footer-card {
  display: flex;
  justify-content: space-between;
  /* Additional styling */
}
{% endcapture %}
{% include code_card.html content=wired_card_css %}

## Conclusion

This journey taught me a valuable lesson: always expect the unexpected when working with Web Components and the Shadow DOM. If you find yourself in a similar predicament, remember that sometimes the simplest solutions, like a well-placed wrapper, can save the day.

Happy coding!