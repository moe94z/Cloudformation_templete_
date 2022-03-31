# awTest

This Respository is an Test Setup for an AWS CodePipeline. It will attempt to build out the following:
<ul>
<li>An <b>Amazon DynamoDB</b> table, that will be used by the AWS Lambda.</li>
<li>An <b>Amazon EC2</b> instance, which will run NGINX and FLask in order to provide a basic web interaction, with two pages, one of which will talk to the AWS Lambda.</li>
<li>An <b>Amazon S3</b>, which will provide basic storage and possibly static web pages.</li>
<li>An <b>AWS ELB</b> Application Load Balancer, which will provide access to web pages and AWS Lamabdas.</li>
<li>An <b>AWS Lambda</b>, which will provide a basic micro-service.</li>
</ul>
It will also deploy all necessary supporting AWS resources, i.e. Security Groups, IAM Roles & Policies, Listeners, and Target Groups.
