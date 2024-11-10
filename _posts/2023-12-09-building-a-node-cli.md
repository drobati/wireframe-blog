---
layout: default
title: "Building a node CLI"
date: 2023-12-09
categories: [node, yargs, openai]
---

# Building a Node CLI

So you want to build a Command-Line Interface (CLI) using Node.js? Well, you're in luck because today we're going to learn how to do just that! We'll be using two awesome libraries called `yargs` and `openai` to make our lives a lot easier.

## Step 1: Set Up Your Project

First things first, let's set up a new Node.js project. Open up your terminal and navigate to the directory where you want to create your project.

{% capture bash_setup %}
mkdir my-node-cli
cd my-node-cli
npm init -y
{% endcapture %}
{% include code_card.html content=bash_setup %}

Now that we have a new project set up, let's install the required dependencies.

{% capture bash_install %}
npm install yargs openai
{% endcapture %}
{% include code_card.html content=bash_install %}

## Step 2: Create Your CLI

Next, let's create a file called `index.js` in the root of your project. This is where we'll write the code for our CLI.

{% capture javascript %}
// index.js

const yargs = require('yargs');
const { openai } = require('openai');

// Define your commands and options using yargs
yargs
  .command('hello [name]', 'Say hello', (yargs) => {
    yargs.positional('name', {
      describe: 'Your name',
      default: 'World',
    });
  }, (argv) => {
    console.log(`Hello, ${argv.name}!`);
  })
  .command('generate [text]', 'Generate text using OpenAI', (yargs) => {
    yargs.positional('text', {
      describe: 'Text to generate',
    });
  }, async (argv) => {
    const text = argv.text || 'Hello, World!';
    const response = await openai.generateText(text);
    console.log(response);
  })
  .demandCommand()
  .help()
  .argv;
{% endcapture %}
{% include code_card.html content=javascript %}


In the code above, we import `yargs` and `openai` libraries. We use `yargs` to define our commands and options, and then we handle those commands with corresponding functions.

You can add as many commands and options as you like, and customize them to fit your needs. Be creative!

## Step 3: Update package.json

Now that we have our CLI code, let's update our `package.json` file to run it.

{% capture package %}
{
  ...
  "scripts": {
    "start": "node cli.js"
  }
  ...
}
{% endcapture %}
{% include code_card.html content=package %}

## Step 4: Test Your CLI

Finally, let's test our CLI. Open up your terminal and run the following command:

{% capture run_hello %}
npm start hello --name John
{% endcapture %}
{% include code_card.html content=run_hello %}

You should see

{% capture command_output %}
Hello, John!
{% endcapture %}
{% include code_card.html content=command_output %}

Congratulations! You've just built your own Node.js CLI. Now go ahead and test out the other command we defined:

{% capture run_joke %}
npm start generate "Tell me a joke"
{% endcapture %}
{% include code_card.html content=run_joke %}

And you should see some hilarious jokes generated by OpenAI.

## Conclusion

In this tutorial, we've learned how to build a simple Node.js CLI using `yargs` and `openai`. With these powerful libraries, you can create all sorts of amazing command-line tools. The possibilities are endless!

So go ahead and have fun exploring what you can do with these tools. Happy coding!