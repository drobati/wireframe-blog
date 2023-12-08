---
layout: default
title: Hack the Planet
slug: blog
---

## Recent Word Soups

{% assign latest_post = site.posts.first %}
<div>
  <h3><wired-link href="{{ latest_post.url }}">{{ latest_post.title }}</wired-link></h3>
  <p>{{ latest_post.excerpt }}</p>
  <wired-link href="{{ latest_post.url }}">Read more...</wired-link>
</div>

## All Posts

<div class="post-list">
  {% for post in site.posts %}
    <div class="post-item">
      <svg class="bullet"></svg><wired-link href="{{ post.url }}">{{ post.title }}</wired-link>
      <span class="post-date">{{ post.date | date_to_string }}</span>
    </div>
  {% endfor %}
</div>