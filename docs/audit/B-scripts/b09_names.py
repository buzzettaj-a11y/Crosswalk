from _common import *
cases = [
 "Smith, John", "Smith, John A", "Smith, John A.", "Smith, John Jr", "Smith Jr, John", "Smith, John, Jr", "Smith, Jr., John", "Smith, John III", "John A Smith", "John Smith", "John Smith Jr", "John Smith Jr.", "John A. Smith Jr.", "John Smith, Jr.", "John Smith III", "John Smith II", "John Smith IV",
 "John Smith Sr", "John Smith 2nd", "John Smith V", "John Smith VI", "John Smith 3rd",
 "Maria de la Cruz", "Maria De La Cruz", "de la Cruz, Maria", "De La Cruz, Maria Elena", "Maria Elena de la Cruz", "Martin Van Buren", "Van Buren, Martin", "Martin Van Der Berg", "Ludwig van Beethoven", "Jose Maria Garcia", "Jose Maria Garcia Lopez", "Ana Maria Garcia-Lopez", "Mary Smith-Jones", "Mary Ann Smith-Jones",
 "Garcia Lopez, Ana", "Ana Garcia Lopez", "Ana M Garcia Lopez", "Ana Maria Garcia Lopez",
 "Madonna", "Cher", "J Smith", "J. Smith", "J R Smith", "J.R. Smith", "J.R. Smith Jr", "Smith, J", "Smith, J R", "Smith, J.R.", "Smith,J", "SMITH,JOHN", "smith, john",
 "McDonald, Ronald", "Ronald McDonald", "MACDONALD, RONALD", "O'Brien, Pat", "Pat O'Brien", "Pat O Brien", "D'Angelo, Tony", "Mary-Jane Watson", "Watson, Mary-Jane", "Mary Jane Watson", "Jean-Luc Picard", "Picard, Jean-Luc",
 "Dr. John Smith", "Mr John Smith", "Mrs. Jane Doe", "John Smith, MD", "John Smith PhD", "Rev. John Smith", "Smith, John (Johnny)", "John 'Johnny' Smith", "John (Jack) Smith", "John Smith (Jr)", "Smith, John Mr",
 "Li Wei", "Wei Li", "Wang Xiaoming", "Kim, Soo Jin", "Soo Jin Kim", "Kim Soo Jin", "Nguyen Van An", "Van An Nguyen", "Abdul Rahman Al Sayed", "Mohammed bin Salman", "Mohamed Ali", "Ali, Mohamed",
 "Smith John", "Smith, John Q Public", "John Quincy Adams", "John Quincy Adams Jr", "Mary Beth Smith Jones", "Smith,", ",John", "John,", "Smith, John, Mary",
 "SMITH JR, JOHN", "Smith III, John", "Smith, III John", "Smith, John Edward", "Smith, John Edward Jr", "Jr Smith", "Jr", "III",
 "Juan C. De La Rosa", "De La Rosa Juan C", "Rosa, Juan De La", "Tran, Thi Mai", "Thi Mai Tran",
]
for c in cases:
    d = engine.split_jammed_name(c)
    print(f"{c!r:34} -> first={d['first']!r:14} mid={d['middle']!r:5} last={d['last']!r}")
