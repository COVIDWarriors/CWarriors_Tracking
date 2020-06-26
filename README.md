# COVIDWarriors

May 24th 2020, I've been working on this code for some days now, but, today my family has lost a very loved one, one of the most beatiful souls I have met in my life, María de Mar, my wife's cousin almost sister. It is not the SARS-CoV2, but triple negative breast cancer, that has severed her life after a five years fight. I want this code to help fight another beast that is severing too many lives to be a tribute to her all that are and will be missed. If I can, I will be coding the whole day, so the first run happens this hard day for me.

And it happened, and it run that day. The first published version has some extra improvements, but it is called the "Mar" release, anyhow.

--------------
# What's this code for

This code simulates the movement of racks with samples through robotic liquid handling stations, organised as A, B and C, following the methods required to amplify SARS-CoV2 genetic material for rPCR detection.

--------------
# Installation

- Add 'tracing' to the project installed apps in settings.
- Add a refresh interval for displaying the robot page while waiting for updates form the real hardware in setings as TRACING_REFRESH in seconds.
- Add the application to the project urls.py with
      ```python
      url(r'^tracing/', include('tracing.urls')),
      ```
- Finally, _makemigrations_ and _migrate_

--------------
# Usage

1. Create robots and operators using the admin interface.
2. Go to your project "tracing" URL with a browser.
3. Using the leftmost button on the "controls" pannel on top, load a sample batch from a CSV file, that MUST (RFC 2119) have a column named "code" that contains the sample codes. All other columns are ignored. You may load an "empty" batch if you do not have a file, sample codes will be added without verification of existence.
4. Then on, the process is like "real life": you prepare empty racks for the samples, and place them on the appropriate locations on the robots.
5. Racks appear on top of the robots where they can be placed.
6. If your protocols have calls to communicate movements to the tracing application (using HTTP requests), you can start the "refresh process" that will anotate sample moves and change robot states accordingly. If there is no communication of real moves, removing the racks from the robot representations will move the samples to the "exit" rack.

--------------
# Acknowledgements

This code has been developed using the knowledge shared by:

- Aitor Gastaminza
- Álex Gasulla
- Ramón Martínez Palomares

And the invaluable input and ideas from Rocio Teresa Martínez Nuñez, and improvement sugestions from Mercedes Pérez.

