from _common import *
import column_check
def guess(cols): 
    m = engine.guess_mapping(cols); return {k: v for k, v in m.items() if v}
print("== guess_mapping ==")
tests = [
 ["First Name","Last Name","Client ID","Mailing Address","Mailing City","Mailing State","Mailing Zip","Home Address","Home City","Home State","Home Zip"],
 ["First Name","Last Name","Client ID","Home Address","Home Zip","Mailing Address","Mailing Zip"],
 ["First Name","Last Name","Client ID","Address Line 2","Address Line 1","City","State","Zip"],
 ["First Name","Last Name","Client ID","Street Address 2","Street Address","City","State","Zip"],
 ["First Name","Last Name","Client ID","Apt","Address","City","State","Zip"],
 ["First Name","Surname","Last Visit","Client ID","Address","City","State","Zip"],
 ["First Name","Last Seen","Last Name","Client ID","Address","City","State","Zip"],
 ["First Name","Last Name","Case ID","Client ID","Address","City","State","Zip"],
 ["First Name","Last Name","Program ID","Household ID","Address","City","State","Zip"],
 ["First Name","Last Name","Parent ID","Client ID","Address","City","State","Zip"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip Plus 4","Zip"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","ZIP Code of Employer"],
 ["First Name","Last Name","Client ID","Address","Birth City","City","State","Zip"],
 ["First Name","Last Name","Client ID","Address","Birth State","State","Zip"],
 ["First Name","Last Name","Client ID","Address","Place of Birth City","City of Residence","State","Zip"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","Program Start Date","Program"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","Program Start Date"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","Service Date","Service Provider"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","Referral Source","Program Status","Program Name"],
 ["First Name","Last Name","Client ID","Address","City","State","Zip","Service Notes","Service"],
 ["Provider First Name","Provider Last Name","Client First Name","Client Last Name","Client ID","Address","City","State","Zip"],
 ["Caseworker First","Caseworker Last","First Name","Last Name","Client ID","Address","City","State","Zip"],
 ["Emergency Contact First Name","Emergency Contact Last Name","First Name","Last Name","ID","Address","City","State","Zip"],
 ["Name First","Name Last","ID","Address","City","State","Zip"],
 ["FNAME","LNAME","ID","Address","City","State","Zip"],
 ["Given Name","Family Name","ID","Street","Borough","ST","Postal Code"],
 ["Forename","Surname","ID","Street","Borough","ST","Postal Code"],
]
for cols in tests:
    print(cols); print("    ->", guess(cols))
