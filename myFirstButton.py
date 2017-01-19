# January 19th, 2017 CISC 472 Homework

# A function that creates a button called myFirstButton
# When the button appears in slicer 3D, it displays 'Push Me'
# When pushed, 'Button Pushed' prints in the console

def myFirstButton()
  print('Button Pushed')

mareenaButton = qt.QPushButton('Push Me')
mareenaButton.connect('clicked()', myFirstButton)
mareenaButton.show()
